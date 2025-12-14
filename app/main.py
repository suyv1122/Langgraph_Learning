# 13. app/main.py（FastAPI）
from typing import Optional
import uuid

from fastapi import FastAPI
from pydantic import BaseModel
from app.router_graph import router_graph
from app.config import settings
from app.db.redis_session import load_session, save_session

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
    session_id: Optional[str] = None
    active_route: Optional[str] = None

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


# v4测试
# curl -X POST http://127.0.0.1:8002/chat \
#   -H "Content-Type: application/json" \
#   -d '{"text":"我下周二想请一天年假","user_role":"public","requester":"peter"}'


# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)

# Terminal % uvicorn app.main:app --reload --port 8002

