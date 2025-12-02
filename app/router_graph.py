from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from app.rag.qa_graph import build_qa_graph

class RouterState(TypedDict, total=False):  # 顶层状态结构，total=False表示其下所有字段都是可选的
    question: str # 给QA的问题
    test: str # 用户原始文本
    user_role: str # 用户角色
    mode: str # 模式标记，如qa, rag, kb等
    answer: str # 答案
    docs: list[Any] # QA检索到的文档列表

def decide_route(state: RouterState) -> str:    # 决定走向何路由
    mode = (state.get('mode') or '').lower().strip()
    if mode in {'qa', 'rag', 'kb'}:
        return mode
    return 'qa' # FIXME: 这个代码目前总会返回QA任务图

def route_node(state: RouterState) -> dict: # 路由前的占位节点，返回{}表示不修改状态
    return {}

def build_router_graph():   # FIXME: 同样永远返回QA任务图，后续更新图需要修改此处
    qa_graph = build_qa_graph()

    g = StateGraph(RouterState)

    g.add_node('route', route_node)
    g.add_node('qa', qa_graph)

    g.add_edge(START, 'route')

    g.add_conditional_edges(
        'route',
        decide_route,
        {'qa':'qa'}
    )

    g.add_edge('qa', END)

    return g.compile()

router_graph = build_router_graph()