# 13. app/main.py（FastAPI）
import time
import uuid
from typing import Optional

from fastapi import FastAPI, Depends, Form, UploadFile, File, HTTPException
from pathlib import Path

from app.db import kb_db
from app.deps import get_vs
from app.ingestion.loader import load_single_file, split_with_visibility
from app.model.auth_model import ChatResp, ChatReq, UserInDB
from app.router_graph import router_graph
from app.config import settings
from app.db.redis_session import load_session, save_session

from app.api.auth_api import router as auth_router, get_current_user
from app.api.rbac_api import router as rbac_router
from app.api.kb_api import router as kb_router
from app.api.audio_api import router as audio_router
from app.service.rbac_service import check_permission

SESSIONS: dict[str, dict] = {}
settings.memory_dir.mkdir(parents=True, exist_ok=True)

# 项目根目录是 `app/` 目录的父目录。
# Project root is the parent of the `app/` directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DOCS_DIR = DATA_DIR / "docs"
DATA_DOCS_DIR.mkdir(parents=True, exist_ok=True)

print(">>> USING MAIN:", __file__)

app = FastAPI(title="Enterprise KB Assistant")
app.include_router(auth_router)
app.include_router(rbac_router)
app.include_router(kb_router)
app.include_router(audio_router)


@app.post("/chat", response_model=ChatResp)
def chat(req: ChatReq):
    payload = req.model_dump()
    text = payload.get('text') or payload.get('question') or ''

    # 1) get or create session id
    # 1) 获取或创建一个会话id
    sid = payload.get('session_id') or f'sid-{uuid.uuid4().hex[:10]}'
    payload['session_id'] = sid

    # 2) load previous state from redis and merge
    # 2) 从 Redis 加载先前状态并合并
    prev_state = load_session(sid)
    if prev_state:
        merged = {**prev_state, **payload}
        merged['text'] = text
        payload = merged

    # 3) run router graph
    # 3) 运行路由图
    out = router_graph.invoke(payload)

    # 4) save new state to redis
    # 4) 保存新状态到redis数据库
    new_state = {**payload, **out}
    save_session(sid, new_state)

    return {
        'answer': out.get('answer'),
        'session_id': sid,
        'active_route': new_state.get('active_route')
    }

@app.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    visibility: str = Form("public"),
    doc_id: Optional[str] = Form(None),
    overwrite: bool = Form(False),
    current_user: UserInDB = Depends(get_current_user),
):
    check_permission(current_user, "kb.manage_docs")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")

    visibility = (visibility or "public").strip().lower()
    doc_id = (doc_id or f"doc-{uuid.uuid4().hex[:12]}").strip()

    existed = kb_db.get_kb_document(doc_id)
    if existed and not overwrite:
        raise HTTPException(status_code=409, detail=f"doc_id already exists: {doc_id}")

    if existed and overwrite:
        from app.rag.chroma_admin import delete_by_doc_id

        try:
            delete_by_doc_id(doc_id)
        except Exception:
            pass

    suffix = Path(file.filename).suffix
    safe_name = f"{int(time.time())}_{uuid.uuid4().hex}{suffix}"
    save_path = DATA_DOCS_DIR / safe_name

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    save_path.write_bytes(content)

    docs = load_single_file(save_path)
    if not docs:
        raise HTTPException(status_code=400, detail=f"Unsupported or empty file type: {suffix}")

    extra_meta = {
        "original_filename": file.filename,
        "stored_path": str(save_path),
        "uploader_user_id": current_user.id,
        "uploader_username": current_user.username,
        "uploaded_at": int(time.time()),
    }

    chunks = split_with_visibility(docs, visibility=visibility, doc_id=doc_id, extra_meta=extra_meta)

    vs = get_vs()
    vs.add_documents(chunks)
    try:
        vs.persist()
    except Exception:
        pass

    try:
        from app.rag.chroma_admin import count_by_doc_id

        chroma_cnt = count_by_doc_id(doc_id)
    except Exception:
        chroma_cnt = len(chunks)

    try:
        kb_db.upsert_kb_document(
            doc_id=doc_id,
            original_filename=file.filename,
            stored_path=str(save_path),
            visibility=visibility,
            uploader_user_id=current_user.id,
            uploader_username=current_user.username,
            chunk_count=chroma_cnt,
        )
    except Exception:
        pass

    return {
        "saved_as": str(save_path),
        "visibility": visibility,
        "doc_id": doc_id,
        "chunks": chroma_cnt,
        "overwrote": bool(existed and overwrite),
    }
# v4测试
# curl -X POST http://127.0.0.1:8002/chat \
#   -H "Content-Type: application/json" \
#   -d '{"text":"我下周二想请一天年假","user_role":"public","requester":"peter"}'


# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)

# Terminal % unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
# export NO_PROXY="localhost,127.0.0.1,0.0.0.0"
# export no_proxy="localhost,127.0.0.1,0.0.0.0"
# Terminal % uvicorn app.main:app --reload --port 8002
