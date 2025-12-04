from __future__ import annotations
from app.deps import get_vs, get_embeddings
from app.ingestion.loader import load_single_file, split_with_visibility, load_docs, split_docs
from app.config import settings, DOCS_DIR
import time
import uuid
from pathlib import Path
from typing import Optional
import chromadb
from fastapi import FastAPI, UploadFile, File, Form, HTTPException

app = FastAPI(title="Enterprise KB Assistant")
DATA_DOCS_DIR = Path(DOCS_DIR)
DATA_DOCS_DIR.mkdir(parents=True, exist_ok=True)

@app.post('/ingest')
async def ingest(
        file: UploadFile = File(...),
        visibility: str = Form('public'),
        doc_id: Optional[str] = Form(None)
):
    """
    Upload a single document and upsert into Chroma.
    :param - Saves file to ./data/docs/
    :param - Loads & splits into chunks
    :param - Attaches visibility/doc_id metadata
    :param - Upserts into the configured Chroma collection
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail='Empty filename')

    visibility = (visibility or 'public').strip().lower()

    suffix = Path(file.filename).suffix
    safe_name = f'{int(time.time())}_{uuid.uuid4().hex}{suffix}'
    save_path = DATA_DOCS_DIR / safe_name

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail='Empty file')
    save_path.write_bytes(content)

    docs = load_single_file(save_path)
    if not docs:
        raise HTTPException(status_code=404, detail=f'Unsupported or empty file type: {suffix}')

    chunks = split_with_visibility(docs, visibility=visibility, doc_id=doc_id)

    vs = get_vs()
    vs.add_documents(chunks)
    try:
        vs.persist()
    except Exception:
        pass

    return {
        'saved_as': str(save_path),
        'visibility': visibility,
        'doc_id': doc_id,
        'chunks': len(chunks)
    }


@app.post("/reindex")
def reindex(visibility_default: str = Form('public')):
    """
    Full rebuild of the collection from ./data/docs.

    WARNING: This deletes the current collection first.
    """
    visibility_default = (visibility_default or 'public').strip().lower()

    # 1) Delete & recreate collection via chromadb client
    client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    try:
        client.delete_collection(settings.collection_name)
    except Exception:
        pass
    client.get_or_create_collection(settings.collection_name)

    # 2) Rebuild using LangChain wrapper
    vs = get_vs()
    raw_docs = load_docs(str(DATA_DOCS_DIR))
    if not raw_docs:
        return {'chunks': 0, 'docs': 0, 'message': 'No documents found in data/docs'}

    chunks = split_docs(raw_docs)
    for c in chunks:
        c.metadata = dict(c.metadata or {})
        c.metadata.setdefault('visibility', visibility_default)

    vs.add_documents(chunks)
    try:
        vs.persist()
    except Exception:
        pass

    return {'docs': len(raw_docs), 'chunks': len(chunks), 'visibility_default': visibility_default}


@app.get('/')
def root():
    return {'status': 'ok', 'docs': '/docs'}

# uvicorn app.main:app --reload --port 8002

# curl -X POST "http://127.0.0.1:8002/ingest" \
#   -F "file=@制度示例1_员工年假与请假管理办法.docx" \
#   -F "visibility=public"
