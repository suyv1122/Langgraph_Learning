import chromadb
from chromadb import Embeddings
from langchain_chroma import Chroma
from app.config import settings
from app.simplestool.simple_embedding import SimpleEmbedding

# def get_vectorstore(embeddings):
#     # client = chromadb.HttpClient(
#     #     host=settings.chroma_host,
#     #     port=settings.chroma_port
#     # )   # 拿到一个指向chromadb数据库的连接
#     client = chromadb.HttpClient(
#         host=settings.chroma_host,
#         port=settings.chroma_port
#     ) # client 表示得到一个指向chromadb的链接
#     return Chroma(
#         client=client,
#         # collection_name=settings.chroma_collection_name, # 为向量数据库起名
#         collection_name=settings.collection_name,
#         embedding_function=embeddings
#     )  # 当向量数据库存储于本机中(使用chroma库时)，这里应当额外指定一个储存地址，用以存放数据
#
# print("CHROMA_HOST =", settings.chroma_host)
# print("CHROMA_PORT =", settings.chroma_port, type(settings.chroma_port))
# print("COLLECTION  =", settings.collection_name)
def get_vectorstore(embeddings: Embeddings) -> Chroma:
    try:
        client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            tenant=getattr(settings, "chroma_tenant", "default_tenant"),
            database=getattr(settings, "chroma_database", "default_database"),
        )
    except Exception as e:
        # 这里的错误通常发生在“连不上 Chroma / tenant 或 database 不匹配 / Chroma 服务未就绪”。
        # chromadb 有时会把底层异常包成 ValueError 且消息为空，所以我们在这里先把原始异常打印出来。
        raise RuntimeError(
            f"Failed to create Chroma HttpClient: host={settings.chroma_host} port={settings.chroma_port} "
            f"tenant={getattr(settings, 'chroma_tenant', 'default_tenant')} "
            f"database={getattr(settings, 'chroma_database', 'default_database')} err={e!r}"
        )
    vectorstore = Chroma(
        client=client,
        collection_name=settings.collection_name,
        embedding_function=embeddings,
    )
    return vectorstore