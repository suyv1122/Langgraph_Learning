# 融合bm25与dense_qdrant评分即rrf
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class FusionHit:        # 融合结果的数据结构。它表示最终输出的一条命中结果
    doc_id: int         # 表示文档id
    score: float        # 表示融合后的最终分数
    sources: list[str]  # s表示这个文档来自哪些召回来源，比如可能来自bm25、dense，也可能两边都有


def rrf_fusion(
    *,
    bm25: list[tuple[int, float]],  # BM25检索结果列表
    dense: list[tuple[int, float]], # 向量检索结果列表
    k: int = 60,                    # k是RRF的平滑参数，默认为60。其会影响排名权重衰减速度
    top_k: int = 20,                # 表示默认最终返回多少条融合结果
) -> list[FusionHit]:
    rrf: dict[int, float] = {}          # rrf用来存每个文档的最终融合分数。key是doc_id，value是累计得分
    srcs: dict[int, list[str]] = {}     # srcs用来存每个文档来自哪些来源


    def add(rank_list: list[tuple[int, float]], src: str) -> None:
        for r, (doc_id, _score) in enumerate(rank_list, start=1):
            s = 1.0 / (float(k) + float(r))
            rrf[doc_id] = float(rrf.get(doc_id, 0.0)) + s
            srcs.setdefault(doc_id, [])
            if src not in srcs[doc_id]:
                srcs[doc_id].append(src)

    add(bm25, "bm25")   # 第一次调用此函数时，rrf中存放的是纯粹的bm25分数
    add(dense, "dense") # 再次调用add()时，会融合先前储存的bm25与本次的dense

    items = list(rrf.items())   # 字典变成元组的键值对并放入list列表中
    items.sort(key=lambda x: float(x[1]), reverse=True)
    out: list[FusionHit] = []
    for doc_id, sc in items[: max(1, int(top_k))]:
        out.append(FusionHit(doc_id=int(doc_id), score=float(sc), sources=list(srcs.get(int(doc_id), []))))
    return out