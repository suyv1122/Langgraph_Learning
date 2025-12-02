from app.deps import get_vs

if __name__ == "__main__":
    vs = get_vs()

    # 方式1：有些版本可以直接 count
    try:
        print("collection count =", vs._collection.count())
    except Exception as e:
        print("raw count error:", e)

    # 方式2：把所有 doc id 打印看看（小心别几万条）
    try:
        all_docs = vs._collection.get(include=["metadatas", "documents"])
        ids = all_docs.get("ids", [])
        print("total docs =", len(ids))
        if len(ids) > 0:
            print("first doc sample:", {
                "id": ids[0],
                "metadata": all_docs["metadatas"][0],
                "doc": all_docs["documents"][0][:80] + "..."
            })
    except Exception as e:
        print("get() error:", e)