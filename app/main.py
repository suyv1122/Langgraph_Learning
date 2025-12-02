# 13. app/main.py（FastAPI）

from fastapi import FastAPI
from pydantic import BaseModel
from app.router_graph import router_graph

print(">>> USING MAIN:", __file__)

app = FastAPI(title="Enterprise KB Assistant")

class ChatReq(BaseModel):
    text: str
    user_role: str = "public"
    requester: str = "anonymous"

print("ChatReq schema =", ChatReq.model_json_schema())

class ChatResp(BaseModel):
    answer: str

@app.post("/chat", response_model=ChatResp)
def chat(req: ChatReq):
    out = router_graph.invoke(req.model_dump())
    return {"answer": out["answer"]}


# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)

# Terminal % uvicorn app.main:app --reload --port 8002

