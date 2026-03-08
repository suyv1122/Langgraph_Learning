# bm25检索
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from rank_bm25 import BM25Okapi

_RE_WORD = re.compile(r"[A-Za-z0-9_]+", re.UNICODE)


def _tokenize(s: str) -> list[str]: # 利用上方正则表达式做分词操作，此处主要为英文分词
    if not s:
        return []
    return [m.group(0).lower() for m in _RE_WORD.finditer(s)]


@dataclass(frozen=True)
class BM25Hit:      # 精确检索，因此不需要载荷
    doc_id: int     # 文档id
    score: float    # 文档分数


class BM25Index:
    def __init__(self, *, docs: list[tuple[int, str]]):
        self._ids = [int(i) for i, _ in docs]
        corpus = [_tokenize(t) for _, t in docs]    # 每个文档文本都拿去分词，得到token列表组成的corpus
        self._bm25 = BM25Okapi(corpus)

    def search(self, query: str, *, top_k: int) -> list[BM25Hit]:
        # 给定一个查询字符串query，返回前top_k个最相关的文档结果
        q = _tokenize(query)                    # 对问题进行分词
        if not q:
            return []
        scores = self._bm25.get_scores(q)       # 调用rank_bm25库，根据q计算corpus中每一篇文档的BM25分数
        pairs = list(zip(self._ids, scores))    # 将文档id与其对应的分数绑定在一起
        pairs.sort(key=lambda x: float(x[1]), reverse=True) # 之后准备排序输出
        out: list[BM25Hit] = []
        for i, s in pairs[: max(0, int(top_k))]:    # pairs 大概是[(1, 98), (4, 96), (6, 93)]的形状，即(文档id, 评分) 的组合
            out.append(BM25Hit(doc_id=int(i), score=float(s)))
        return out