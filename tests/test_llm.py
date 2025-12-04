# from langchain_ollama import ChatOllama
# import os
#
# def get_llm():
#     print(">>> [get_llm] OLLAMA_HOST env =", os.getenv("OLLAMA_HOST"))
#
#     llm = ChatOllama(
#         model="llama3.2:3b",
#         base_url="http://127.0.0.1:11434",
#         temperature=0.2
#     )
# print(">>> [get_llm] ChatOllama configured with base_url=http://127.0.0.1:11434")

from app.deps import get_llm

def main():
    llm = get_llm()
    res = llm.invoke("只是一个测试：请用一句话说明年假如何申请？")
    print(res)

if __name__ == "__main__":
    main()