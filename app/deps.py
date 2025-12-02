from app.config import settings
from langchain_ollama import ChatOllama, OllamaEmbeddings
from app.rag.vectorstore import get_vectorstore
from app.simplestool.simple_embedding import SimpleEmbedding

def get_llm():
    return ChatOllama(
        model=settings.model_name,
        temperature=0.2,
        streaming=True
    )

def get_embeddings():
    """因兼容问题，调用了本地实现的新embedding方法"""
    # return OllamaEmbeddings(model='nomic-embed-text')
    return SimpleEmbedding(model='nomic-embed-text')

def get_vs():
    return get_vectorstore(get_embeddings())

if __name__ == '__main__':
    print(get_llm())
    print(f'_____________________\n')
    print(get_vs())