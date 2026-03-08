from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SearchMode = Literal["bm25", "dense", "hybrid"]
# bm25表示词法检索，针对关系数据库sql和文档数据库如es，即基于关键词匹配、词频和文档频率之类的传统搜索方式
# dense表示向量检索，即先将查询文本转为向量，再于向量数据库中寻找语义最接近的内容(向量空间内数学距离等查询)
# hybrid表示混合检索，将bm25与dense两种方式结合，一起召回再融合排序


class SearchReq(BaseModel): # 定义知识库搜索接口的请求参数结构
    q: str = Field(min_length=1, max_length=4000)   # q 即为搜索词，即用户输入的问题或查询内容
    mode: SearchMode = "hybrid"
    top_k: int = Field(default=10, ge=1, le=50)     # 此字段表示将要返回多少条搜索结果
    project_id: int | None = None                   # 此字段表示搜索范围可以进一步限定到某个project，属于可选内容


class SearchHit(BaseModel): # 定义单条搜索命中结果的数据结构
    chunk_id: int               # 表示命中的chunk的id
    asset_id: int               # 表示此chunk属于哪个资产，即：属于哪份文档、哪条资料、哪个知识库对象
    score: float                # 表示此命中的相关性分数
    sources: list[str]          # 表示此命中结果来自哪些召回源。
                                #   如在hybrid模式下一条结果可能同时被bm25和dense两边都召回到，
                                #   那么sources里可能就会有两个值
    content: str                # 命中的实际文本内容


class SearchResp(BaseModel): # 定义知识库搜索接口的返回数据结构
    q: str
    mode: SearchMode
    top_k: int
    items: list[SearchHit]      # 搜索结果列表，里面每一项都是一个SearchHit