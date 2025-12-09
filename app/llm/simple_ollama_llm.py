import requests
from langchain_core.messages import BaseMessage

class SimpleOllamaLLM:
    """
    Minimal LLM wrapper for Ollama local models.
    Works with LangGraph and LangChain via .invoke()
    """

    def __init__(self, model: str, base_url: str = "http://127.0.0.1:11434/api/chat"):
        self.model = model
        self.base_url = base_url

    def _call(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        resp = requests.post(self.base_url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        # Chat completion API returns:  {"message": {...}}
        if "message" in data and "content" in data["message"]:
            return data["message"]["content"]

        # fallback
        return str(data)

    def _convert_messages_to_prompt(self, messages):
        """将 LangChain 的 Message 对象列表转换成纯字符串 prompt"""
        lines = []
        for m in messages:
            role = m.type # 'human' / 'system' / 'ai'
            content = m.content
            lines.append(f"{role.upper()}: {content}")
        return '\n'.join(lines)

    # 给 LangChain / LangGraph 用
    def invoke(self, prompt: str):
        # --- 1. 如果收到的是 LangChain messages 列表，进行格式化 ---
        if isinstance(prompt, list) and all(isinstance(m, BaseMessage) for m in prompt):
            prompt = self._convert_messages_to_prompt(prompt)

        return self._call(prompt)