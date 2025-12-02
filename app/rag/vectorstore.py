import chromadb
from langchain_chroma import Chroma
from app.config import settings
from app.simplestool.simple_embedding import SimpleEmbedding

def get_vectorstore(embeddings):
    # client = chromadb.HttpClient(
    #     host=settings.chroma_host,
    #     port=settings.chroma_port
    # )   # 拿到一个指向chromadb数据库的连接
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    return Chroma(
        client=client,
        # collection_name=settings.chroma_collection_name, # 为向量数据库起名
        collection_name=settings.collection_name,
        embedding_function=embeddings
    )  # 当向量数据库存储于本机中(使用chroma库时)，这里应当额外指定一个储存地址，用以存放数据
