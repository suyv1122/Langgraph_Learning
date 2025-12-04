from app.deps import get_vs

if __name__ == "__main__":
    vs = get_vs()

    try:
        print("collection count = ", vs.collection_count())
    except Exception as e:
        print("raw count error: ", e)

    try:
        all_docs = vs._collection.get(include=["metadatas", "documents"])
        ids = all_docs.get("ids", [])
        print("total docs = ", len(ids))
        if ids:
            print("first doc sample:", {
                "id": ids[0],
                "metadata": all_docs["metadatas"][0],
                "doc": all_docs["documents"][0][:80] + "..."
            })
    except Exception as e:
        print("get() error: ", e)