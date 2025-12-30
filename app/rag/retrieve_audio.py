from __future__ import annotations

from app.deps import get_vs

def audio_similarity_search_for_user(query: str, user, k: int = 6):
    vs = get_vs()
    # allowed =compute_allowed_kb_visibilities(user)
    docs = vs.similarity_search(query, k=k, filter={'visibility': {'$in':'public'}})
    return docs, 'public'