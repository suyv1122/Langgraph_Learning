from __future__ import annotations
from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from app.rag.qa_graph import build_qa_graph
from app.workflows.leave.leave_graph import build_leave_graph

class RouterState(TypedDict, total=False):  # 顶层状态结构，total=False表示其下所有字段都是可选的
    question: str # 给QA的问题
    text: str # 用户原始文本，需要兼容 /chat 的字段
    user_role: str # 用户角色
    mode: str # 模式标记，如qa, rag, kb, leave等
    requester: str
    active_route: str


    # --- fields produced by subgraphs that we want to keep across turns ---
    req: dict
    missing_fields: list[str]
    violations: list[str]

    answer: str # 答案
    docs: list[Any] # QA检索到的文档列表
    leave_id: str


def decide_route(state: RouterState) -> str:    # 决定走向何路由
    mode = (state.get('mode') or '').lower().strip()

    active = (state.get('active_route') or '').lower().strip()
    if active == 'leave' and mode not in {'qa', 'rag', 'kb'}:
        return 'leave'

    # 显式mode优先
    if mode in {'qa', 'rag', 'kb'}:
        return 'qa'
    if mode in {'leave', 'hr'}:
        return 'leave'

    # 关键词路由
    text = (state.get('text') or state.get('question') or '').lower()
    if any(k in text for k in ['请假', '年假', '病假', '事假', '休假', '调休', '假期', '请一天假', '请半天假']):
        return 'leave'

    return 'qa'


def route_node(state: RouterState) -> dict: # 路由前的占位节点，返回{}表示不修改状态
    """Router node runnable. Must return dict updates"""
    print("DEBUG TEXT =", state.get("text"), "TEST =", state.get("test"))
    return {'active_route': decide_route(state)}


def build_router_graph():
    qa_graph = build_qa_graph()
    leave_graph = build_leave_graph()

    g = StateGraph(RouterState)

    g.add_node('route', route_node)
    g.add_node('qa', qa_graph)
    g.add_node('leave', leave_graph)

    g.add_edge(START, 'route')

    g.add_conditional_edges(
        'route',
        decide_route,
        {'qa':'qa', 'leave':'leave'}
    )

    g.add_edge('qa', END)
    g.add_edge('leave', END)

    return g.compile()

router_graph = build_router_graph()