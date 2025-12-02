import ollama

resp = ollama.embed(
    model="nomic-embed-text",
    input="测试一下年假怎么申请？"
)

print("ok, got dim =", len(resp["embeddings"][0]))

#   File "/Users/paradice/PycharmProjects/PythonProject2/.venv/lib/python3.13/site-packages/ollama/_client.py", line 189, in _request
#     return cls(**self._request_raw(*args, **kwargs).json())
#                  ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
#   File "/Users/paradice/PycharmProjects/PythonProject2/.venv/lib/python3.13/site-packages/ollama/_client.py", line 133, in _request_raw
#     raise ResponseError(e.response.text, e.response.status_code) from None
# ollama._types.ResponseError:  (status code: 502)