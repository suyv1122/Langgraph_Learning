# test_embeddings.py
from langchain_ollama import OllamaEmbeddings

emb = OllamaEmbeddings(
    model="nomic-embed-text",
    # 如果你不是默认端口，或者有代理，在这里加 base_url
    # base_url="http://localhost:11434",
)

print("开始调 embed_query...")
vec = emb.embed_query("测试一下年假怎么申请？")
print("长度:", len(vec))
print("前 5 维:", vec[:5])

# 响应信息:
# Traceback (most recent call last):
#   File "/Users/paradice/PycharmProjects/PythonProject2/app/test_embeddings.py", line 11, in <module>
#     vec = emb.embed_query("测试一下年假怎么申请？")
#           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "/Users/paradice/PycharmProjects/PythonProject2/.venv/lib/python3.13/site-packages/langchain_ollama/embeddings.py", line 307, in embed_query
#     return self.embed_documents([text])[0]
#            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^
#   File "/Users/paradice/PycharmProjects/PythonProject2/.venv/lib/python3.13/site-packages/langchain_ollama/embeddings.py", line 301, in embed_documents
#     return self._client.embed(
#            ~~~~~~~~~~~~~~~~~~^
#         self.model, texts, options=self._default_params, keep_alive=self.keep_alive
#         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#     )["embeddings"]
#     ^
#   File "/Users/paradice/PycharmProjects/PythonProject2/.venv/lib/python3.13/site-packages/ollama/_client.py", line 393, in embed
#     return self._request(
#            ~~~~~~~~~~~~~^
#       EmbedResponse,
#       ^^^^^^^^^^^^^^
#     ...<9 lines>...
#       ).model_dump(exclude_none=True),
#       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#     )
#     ^
#   File "/Users/paradice/PycharmProjects/PythonProject2/.venv/lib/python3.13/site-packages/ollama/_client.py", line 189, in _request
#     return cls(**self._request_raw(*args, **kwargs).json())
#                  ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
#   File "/Users/paradice/PycharmProjects/PythonProject2/.venv/lib/python3.13/site-packages/ollama/_client.py", line 133, in _request_raw
#     raise ResponseError(e.response.text, e.response.status_code) from None
# ollama._types.ResponseError:  (status code: 502)

# 版本信息:
# (.venv) (base) paradice@paradicedeMacBook-Pro PythonProject2 % pip show langchain-ollama
# Name: langchain-ollama
# Version: 1.0.0
# Summary: An integration package connecting Ollama and LangChain
# Home-page: https://docs.langchain.com/oss/python/integrations/providers/ollama
# Author:
# Author-email:
# License: MIT
# Location: /Users/paradice/PycharmProjects/PythonProject2/.venv/lib/python3.13/site-packages
# Requires: langchain-core, ollama
# Required-by:
# (.venv) (base) paradice@paradicedeMacBook-Pro PythonProject2 % pip show ollama
# Name: ollama
# Version: 0.6.1
# Summary: The official Python client for Ollama.
# Home-page: https://ollama.com
# Author:
# Author-email: hello@ollama.com
# License-Expression: MIT
# Location: /Users/paradice/PycharmProjects/PythonProject2/.venv/lib/python3.13/site-packages
# Requires: httpx, pydantic
# Required-by: langchain-ollama
# (.venv) (base) paradice@paradicedeMacBook-Pro PythonProject2 % ollama --version
# ollama version is 0.12.6