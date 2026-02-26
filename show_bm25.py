from rank_bm25 import BM25Okapi

def tok_en(s: str):
    return s.lower().split()

docs = [
    "bm25 is a lexical retrieval function used in information retrieval",
    "vector search uses embeddings to find semantically similar documents",
    "hybrid retrieval combines bm25 and dense vector retrieval",
    "rrf is a rank-based fusion method robust to score scale differences",
    "fastapi is a modern web framework for building apis in python",
]

corpus = [tok_en(d) for d in docs]
print(corpus)
bm25 = BM25Okapi(corpus=corpus)

query = "bm25 lexical retrieval"
scores = bm25.get_scores(tok_en(query))
ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

print("Query:", query)
for i,s in ranked:
    print(f"{i}  score={s:.4f} {docs[i]}")

# （——————————————————————————————————————

# 中文分词
import thulac
from rank_bm25 import BM25Okapi

thu = thulac.thulac(seg_only=True)

def tok_zh(s: str):
    return [w.strip() for w in thu.cut(s, text=True).split()]

docs_zh = [
    "BM25是经典的词法检索打分函数，用于信息检索系统。",
    "向量检索使用embedding来召回语义相近的文档。",
    "混合检索把BM25和向量召回结合起来，提升召回率与鲁棒性。",
    "长度归一化可以避免长文档天然获得更高分。",
    "语言检测有助于选择合适的分词与检索策略。",
]

corpus = [tok_zh(d) for d in docs_zh]
print(corpus)
bm_zh = BM25Okapi(corpus, k1=1.5, b=0.75)

q_zh = "BM25 词法 检索 长度 归一化"
q_tokens = tok_zh(q_zh)

scores = bm_zh.get_scores(q_tokens)
ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:5]

print("Query:", q_zh)
for i, s in ranked:
    print(f"{i} score={s:.4f} {docs_zh[i]}")