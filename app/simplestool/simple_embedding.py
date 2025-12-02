from typing import List
import requests

class SimpleEmbedding:
    """
    这是一个不得已的兼容写法，由于ollama模块可能有问题：
        使用HTTP请求调用Ollama /api/embed
        完全绕过python的ollama客户端
    """
    def __init__(self, model: str = 'nomic-embed-text', base_url: str = 'http://localhost:11434'):
        self.model = model
        self.base_url = base_url.rstrip('/')

    def _call_ollama_embed(self, text: str) -> List[float]:
        """
        调用本地Ollama embed API，返回单文本向量
        """
        url = f"{self.base_url}/api/embed"
        payload = {
            "model": self.model,
            "input": [text],
        }

        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code != 200:
            # 便于调试的设置，直接将错误抛出到终端
            raise RuntimeError(f'Ollama embed failed: {resp.status_code} {resp.text}')

        data = resp.json()
        # 输出格式为 {'model':..., 'embeddings':[[...]]} 类型为json
        return data['embeddings'][0]

    def embed_query(self, query: str) -> List[float]:
        """
        用于 Chroma / retriever 的单个查询向量化
        """
        return self._call_ollama_embed(query)

    def embed_documents(self, docs: List[str]) -> List[List[float]]:
        """
        用于构建向量库的多文档向量化
        """
        return [self._call_ollama_embed(d) for d in docs]

# FIXME: 检查ollama模块下的 ollama.__version__ 以确定输出格式是否有问题


import ollama
class AbandonedSimpleEmbedding:
    """
    此代码被废弃于
        2025年12月 2日 星期二 11時59分13秒 CST
    由于现阶段 Python的 ollama模块 不太对劲


    一个最小可运行的本地embedding适配器
    ---------------------------------------------------------
    这被用于解决目前环境下langchain-ollama的embedding与新版api不兼容的问题:
    - ollama server 版本为 0.12.x
    - nomic-embed-text 的 embedding API 只能手动调用
    因此此处实现一个最小可用的 embedding 类，用于 RAG / LangGraph。
    """
    def __init__(self, model: str = 'nomic-embed-text'):
        """
        :param model: 本地向量化模型名称，必须存在于本地ollama list中
        """
        self.model = model

    def _call_ollama_embed(self, text: str) -> List[float]:
        """
        调用 本地Ollama 的 embed API
        返回单个文本的 embedding 向量 (list[float])
        """
        try:
            response = ollama.embed(
                model=self.model,
                input=text
            )
            # 新版API格式为: {'embeddings':[ [...向量...] ]}
            return response["embeddings"][0]
        except Exception as e:
            print(f"[SimpleEmbedding ERROR] text={text!r}")
            print(f"[SimpleEmbedding ERROR] model={self.model}")
            print(f"[SimpleEmbedding ERROR] raw_error={e!r}")
            raise

    def embed_documents(self, docs: List[str]) -> List[List[float]]:
        """
        多文本向量化，用于向量数据库
        :param docs: 文本列表
        :return: 向量列表
        """
        return [self._call_ollama_embed(doc) for doc in docs]

    def embed_query(self, query: str) -> List[float]:
        """
        单次查询向量化，用于检索
        """
        return self._call_ollama_embed(query)