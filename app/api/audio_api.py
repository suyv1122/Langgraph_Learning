from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import List, Optional, Iterable

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from langchain_core.messages import HumanMessage, SystemMessage
from starlette.responses import StreamingResponse  # starlette是FastAPI自带附加依赖

from app.api.auth_api import UserInDB, get_current_user
from app.config import settings
from app.db import audio_db, audio_job_db
from app.deps import get_audio_vs, get_llm
from app.model.audio_model import (
    AudioIngestAsyncResp,
    AudioJobResp,
    AudioDocDetail,
    AudioSearchResp,
    AudioSearchHit,
    AudioCitation,
)
from app.service.rbac_check_permission import require_kb_manage_docs
from app.service.rbac_service import allowed_kb_visibilities
from app.tasks.audio_tasks import audio_ingest_task

router = APIRouter(prefix="/audio", tags=["audio"])

AUDIO_DIR = Path(getattr(settings, "audio_dir", "data/audio"))
CLIP_DIR = Path(getattr(settings, "audio_clip_dir", "data/audio_clips"))
WAV_DIR = Path(getattr(settings, "audio_wav_dir", "data/audio_wav"))


def _normalize_visibility(v: str) -> str:
    v = (v or "").strip().lower()
    return v if v in ("public", "internal") else "public"


def _get_allowed_and_check(user: UserInDB, doc_visibility: Optional[str] = None) -> List[str]:
    perms = getattr(user, "permissions", None)
    allowed = allowed_kb_visibilities(perms)
    if "public" not in allowed:
        allowed = ["public"] + [x for x in allowed if x != "public"]

    if doc_visibility:
        vis = (doc_visibility or "").strip().lower()
        if vis not in set(allowed):
            raise HTTPException(status_code=403, detail="no permission to access this audio")

    return allowed


def _get_allowed_set(user: UserInDB) -> set[str]:
    return set(_get_allowed_and_check(user))


def _absolute_base(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _clip_url(base: str, audio_id: str, start_ms: int, end_ms: int) -> str:
    return f"{base}/audio/docs/{audio_id}/clip?start_ms={start_ms}&end_ms={end_ms}"


def _build_langchain_messages(messages: list[dict[str, str]]):
    """
    将我们自己构造的message转换成langchain能识别的消息对象列表，是一个小的工具类
    这里的message本意是这样的
    [
        {"role": "system", "content": "你是一个音频问答助手。"},
        {"role": "user", "content": "请根据音频内容回答问题。"}
    ]
    """
    msg_objs = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        msg_objs.append(
            SystemMessage(content=content) if role == "system" else HumanMessage(content=content)
        )
    return msg_objs


def _openai_chat_complete(*, messages: list[dict[str, str]]) -> str:
    llm = get_llm()
    try:
        result = llm.invoke(_build_langchain_messages(messages))
        return (result.content or "").strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 调用出错: {e}")


def _openai_stream(*, messages: list[dict[str, str]]) -> Iterable[str]:
    """参数和之前的一样，返回值是Iterable[str]，主要我们后面用yield流式输出做好基础"""
    llm = get_llm()
    try:
        for chunk in llm.stream(_build_langchain_messages(messages)):
            if chunk.content:
                yield chunk.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 流式调用出错: {e}")


def _build_rag_messages(question: str, citations: list[AudioCitation], system_prompt: Optional[str]) -> list[
    dict[str, str]]:
    sys = (system_prompt or "").strip() or (
        "你是企业知识库助手，回答必须基于给定的【音频片段】内容。"
        "如果片段不足以回答，就明确说“不确定/片段中没有”。"
        "回答要简洁，并在结尾给出引用列表（用 [1][2]... 标注）。"
    )

    ctx_lines = [
        f"[{i}] audio_id={c.audio_id} segment_id={c.segment_id} "
        f"start_ms={c.start_ms} end_ms={c.end_ms}\n片段文本：{c.text}"
        for i, c in enumerate(citations, start=1)
    ]
    ctx = "\n\n".join(ctx_lines) if ctx_lines else "（无片段）"

    user = (
        f"问题：{question}\n\n"
        f"【音频片段】\n{ctx}\n\n"
        "要求：\n1) 只用片段信息回答。\n"
        "2) 如果引用了某个片段，请用 [序号] 标注。\n"
        "3) 不要编造片段里没有的信息。"
    )

    return [{"role": "system", "content": sys}, {"role": "user", "content": user}]


def _search_audio_segments(vs, query: str, allowed_vis: list[str], k: int, audio_id: Optional[str] = None):
    where = {"visibility": {"$in": allowed_vis}}
    if audio_id:
        where = {"$and": [{"visibility": {"$in": allowed_vis}}, {"audio_id": audio_id}]}
    fetch_k = min(max(k * 5, k), 50)
    return vs.similarity_search_with_score(query, k=fetch_k, filter=where)


def _build_audio_hits(docs_scores, allowed_vis_set: set[str], base: str, mode: str = "hit"):
    """把向量搜索结果docs_scores转换成业务层能用的结构AudioSearchHit或AudioCitation"""
    results, seen = [], set()  # seen用于防止重复片段，比如多个检索结果指向相同音频区间
    for doc, score in docs_scores:
        md = doc.metadata or {}
        audio_id = str(md.get("audio_id") or "").strip()
        segment_id = str(md.get("segment_id") or "").strip()
        if not (audio_id and segment_id):
            continue
        try:
            start_ms, end_ms = int(md.get("start_ms", 0)), int(md.get("end_ms", 0))
        except Exception:
            continue
        if start_ms < 0 or end_ms <= start_ms:
            continue
        key = (audio_id, segment_id, start_ms, end_ms)
        if key in seen:
            continue
        seen.add(key)  # 生成唯一key，即同一个片段唯一标识，所以这里用了set集合
        db_doc = audio_db.get_audio_document(audio_id)
        if not db_doc:
            continue
        if (db_doc.get("visibility") or "").strip().lower() not in allowed_vis_set:
            continue
        text = (doc.page_content or "").strip()
        if mode == "hit":  # hit搜索结果列表/query，返回AudioSearchHit
            results.append(AudioSearchHit(
                audio_id=audio_id, segment_id=segment_id,
                start_ms=start_ms, end_ms=end_ms, text=text,
                score=float(score) if score is not None else None,
                clip_url=_clip_url(base, audio_id, start_ms, end_ms)
            ))
        else: # citation问答引用/ask/stream接口，结果是AudioCitation
            results.append(AudioCitation(
                audio_id=audio_id, segment_id=segment_id,
                start_ms=start_ms, end_ms=end_ms, text=text,
                clip_url=_clip_url(base, audio_id, start_ms, end_ms),
                score=float(score) if score is not None else None
            ))
    return results


@router.post("/ingest", response_model=AudioIngestAsyncResp)
async def ingest_audio(
        file: UploadFile = File(...),
        visibility: str = Form("public"),
        audio_id: Optional[str] = Form(None),
        language: Optional[str] = Form(None),
        overwrite: bool = Form(False),
        delete_old_file: bool = Form(False),
        current_user: UserInDB = Depends(get_current_user),
):
    require_kb_manage_docs(current_user)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")

    visibility = _normalize_visibility(visibility)
    audio_id = (audio_id or f"aud-{uuid.uuid4().hex[:12]}").strip()
    job_id = f"job-{uuid.uuid4().hex[:12]}"

    if audio_db.is_audio_running(audio_id):
        raise HTTPException(status_code=409, detail="audio is running, try later")

    existed = audio_db.get_audio_document(audio_id)
    if existed and not overwrite:
        raise HTTPException(status_code=409, detail="audio_id already exists; set overwrite=true")

    old_stored_path = existed["stored_path"] if existed else None
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename).suffix or ".bin"
    raw_path = AUDIO_DIR / f"{int(time.time())}_{uuid.uuid4().hex}{suffix}"
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    raw_path.write_bytes(raw_bytes)

    audio_db.upsert_audio_document(
        audio_id=audio_id,
        original_filename=file.filename,
        stored_path=str(raw_path),
        duration_ms=0,
        language=language,
        visibility=visibility,
        status="queued",
        uploader_user_id=int(getattr(current_user, "id", 0) or 0) or None,
        uploader_username=getattr(current_user, "username", None),
        segment_count=0,
    )

    audio_job_db.create_job(
        job_id,
        audio_id,
        overwrite=bool(overwrite),
        delete_old_file=bool(delete_old_file),
        old_stored_path=old_stored_path if overwrite else None,
    )

    async_result = audio_ingest_task.apply_async(
        args=[job_id, audio_id],
        queue=getattr(settings, "celery_audio_queue", "audio"),
    )
    audio_job_db.bind_task(job_id, async_result.id)

    return AudioIngestAsyncResp(
        job_id=job_id,
        audio_id=audio_id,
        stored_as=str(raw_path),
        visibility=visibility,
        celery_task_id=async_result.id,
        status_url=f"/audio/jobs/{job_id}",
    )


@router.post("/ask/stream")
def ask_audio_stream(
    req: dict,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
):
    question = (req.get("question") or "").strip()
    audio_id = req.get("audio_id")
    k = max(1, min(int(req.get("k") or 6), 20))

    if not question:
        raise HTTPException(status_code=400, detail="question is empty")

    allowed_vis = _get_allowed_and_check(current_user)
    allowed_vis_set = set(allowed_vis)
    vs = get_audio_vs()
    base = _absolute_base(request)

    docs_scores = _search_audio_segments(vs, question, allowed_vis, k, audio_id)
    citations = _build_audio_hits(docs_scores, allowed_vis_set, base, mode="citation")

    messages = _build_rag_messages(question, citations, None)

    def event_stream():
        yield f"event: meta\ndata: { {'question': question, 'citations': [c.model_dump() for c in citations]} }\n\n"
        for chunk in _openai_stream(messages=messages):
            yield f"event: token\ndata: {chunk}\n\n"
        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/jobs/{job_id}", response_model=AudioJobResp)
def get_audio_job(job_id: str, current_user: UserInDB = Depends(get_current_user)):
    require_kb_manage_docs(current_user)
    row = audio_job_db.get_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    return row


@router.post("/jobs/{job_id}/cancel")
def cancel_audio_job(job_id: str, current_user: UserInDB = Depends(get_current_user)):
    require_kb_manage_docs(current_user)
    ok = audio_job_db.request_cancel(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job_id": job_id, "cancel_requested": True}


@router.get("/docs/{audio_id}", response_model=AudioDocDetail)
def get_audio_doc(audio_id: str, current_user: UserInDB = Depends(get_current_user)):
    require_kb_manage_docs(current_user)
    row = audio_db.get_audio_document(audio_id)
    if not row:
        raise HTTPException(status_code=404, detail="audio not found")
    return row


@router.get("/query", response_model=AudioSearchResp)
def query_audio(
        request: Request,
        q: str = Query(..., min_length=1),
        k: int = Query(6, ge=1, le=20),
        current_user: UserInDB = Depends(get_current_user),
) -> AudioSearchResp:
    allowed_vis = _get_allowed_and_check(current_user)
    allowed_vis_set = set(allowed_vis)
    vs = get_audio_vs()
    base = _absolute_base(request)

    docs_scores = _search_audio_segments(vs, q, allowed_vis, k)
    hits = _build_audio_hits(docs_scores, allowed_vis_set, base, mode="hit")

    return AudioSearchResp(q=q, k=k, allowed_visibilities=allowed_vis, hits=hits)

@router.get("/search", response_model=AudioSearchResp)
def search_audio(*args, **kwargs):
    return query_audio(*args, **kwargs)