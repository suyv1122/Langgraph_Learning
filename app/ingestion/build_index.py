from pathlib import Path
from app.config import settings
from app.ingestion.loader import load_docs, split_docs
from app.deps import get_embeddings, get_vs

# def main():
#     docs = split_docs(load_docs())
#     vs = get_vs()
#     vs.add_documents(docs)
#     try:
#         vs.persist()        # 持久化，防止关机后内容丢失
#     except Exception:
#         pass
#     print(f"Indexed {len(docs)} chunks into Chroma.")

def main():
    print("CWD = ", Path.cwd())
    print("DOCS_DIR = ", settings.docs_dir)

    raw_docs = load_docs()
    print("RAW DOCS = ", len(raw_docs))

    docs = split_docs(raw_docs)
    print("CHUNKS = ", len(docs))

    if not docs:
        print("没有任何文档被切片，检查 docs_dir / 路径 设置")
        return

    vs = get_vs()
    vs.add_documents(docs)
    print(f"Indexed {len(docs)} chunks into {len(docs)} Chroma.")

if __name__ == "__main__":
    main()
    # emb = get_embeddings()
    # emb.embed_query("for testing")


