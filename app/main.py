# 13. app/main.py（FastAPI）
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel
from app.router_graph import router_graph
from app.config import settings

SESSIONS: dict[str, dict] = {}
settings.memory_dir.mkdir(parents=True, exist_ok=True)

print(">>> USING MAIN:", __file__)

app = FastAPI(title="Enterprise KB Assistant")

class ChatReq(BaseModel):
    text: str
    user_role: str = "public"
    requester: str = "anonymous"
    session_id: Optional[str] = None

print("ChatReq schema =", ChatReq.model_json_schema())

class ChatResp(BaseModel):
    answer: str

@app.post("/chat", response_model=ChatResp)
def chat(req: ChatReq):
    # out = router_graph.invoke(req.model_dump())
    payload = req.model_dump()
    sid = payload.get("session_id")

    if sid and sid in SESSIONS:
        prev = SESSIONS[sid]
        merged = {**prev, **payload}
        merged['text'] = payload.get('text')
        payload = merged

    out = router_graph.invoke(payload)
    if sid:
        SESSIONS[sid] = {**payload, **out}
    return {"answer": out["answer"]}


# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)

# Terminal % uvicorn app.main:app --reload --port 8002

