import requests

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

    # 给 LangChain / LangGraph 用
    def invoke(self, prompt: str):
        return self._call(prompt)