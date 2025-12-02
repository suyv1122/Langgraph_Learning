from typing import TypedDict, List, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage

from app.rag.prompts import QA_SYSTEM, QA_USER
from app.deps import get_llm, get_vs

"""下面是LangGraph中的状态结构，类似上下文的形式：
    · question: 用户问的问题
    · user_role: 用户角色，例如employee, hr, admin；用于权限控制
    · docs: 检索到的文档列表(LangChain的Document)
    · answer: 最终给用户的回答
    · messages: 预留的消息列表(目前代码没用到，日后用于储存对话历史)
整个图的运行便是围绕这个字典不断修改"""


class QAState(TypedDict):
    question: str
    text: str
    user_role: str
    docs: List[Any]
    answer: str
    messages: List[Any]


def decide_retrieve(state: QAState) -> str:
    """
    路由节点：决定是否检索知识库，或是直接回答。
    返回值必须对应add_conditional_edges里的key
    """
    # 为了快速上线测试，要求它总是先检索
    return 'retrieve'

def decide_retrieve_node(state: QAState) -> dict:
    """
    节点runnable: 必须返回dict
    此处只是一个no-op节点，真正路由在decide_retrieve()中完成
    :param state:
    :return:
    """
    return {}

def retrieve(state: QAState) -> dict:
    """从Chroma检索相关文档，按可见性过滤"""
    vs = get_vs()
    # 转成检索器retriever
    # k:8 - 最多取八条匹配文档
    # filter 使用向量库的元数据过滤，只要visibility于['public', state['user_role']]里的文档。
    # 也就是所有人都能看到visibility='public的文档；某个角色的人还能看到visibility=该角色的文档。
    # 前提是在建立索引时写入了metadata['visibility']，否则这个过滤不会起作用。
    role = state.get('user_role', 'public')
    query = state.get('question') or state.get('text') or ''

    retriever = vs.as_retriever(
        search_kwargs={
            'k': 8,
            'filter': {'visibility': {'$in': ['public', role]}}
        }
    )
    docs = retriever.invoke(query)  # 真正执行检索

    if not docs:
        retriever2 = vs.as_retriever(search_kwargs={'k':8})
        docs = retriever2.invoke(query)
        return {'docs': docs, 'question': query, 'debug': 'fallback_unfiltered'}
    return {'docs': docs, 'question':query, 'debug':'filtered'}  # LangGraph约定节点返回的是一个局部state更新。会被合并到全局state中，
    # 相当于state['docs'] = docs


def grade_evidence(state: QAState) -> str:
    """判断检索证据是否足够。此处简化了docs：空便返回bad, 不空返回good"""
    return 'good' if state.get('docs') else 'bad'


def generate_answer(state: QAState) -> dict:
    """带引用生成答案"""
    llm = get_llm()
    docs = state.get('docs', [])

    # 准备上下文————将检索到的文档拼成一段context
    context = '\n\n'.join(
        f'[{i + 1}]{d.page_content}\n(source={d.metadata.get("source")}, page={d.metadata.get("page")})' for i, d in
        enumerate(docs[:6])  # 只拿前面六条文档，避免提示词过长
        # 每个文档前添加了[i]引用，方便LLM后续引用，前面的提示词有提到此要求
    )
    # 准备提示词
    prompt = QA_USER.format(question=state['question'], context=context)
    # 拼接消息列表，AIMessage视为预设指令，HumanMessage是本次真正发出的内容
    messages = [AIMessage(content=QA_SYSTEM), HumanMessage(content=prompt)]
    ans = llm.invoke(messages).content  # 大模型返回结果
    return {'answer': ans}


def refuse_of_clarify(state: QAState) -> dict:
    """无证据时的兜底回复，即 grade_evidence 为 bad 时通向此处"""
    return {
        'answer': '未能于当前可见知识库中找到足够证据以组织回答。请提供更具体的关键词/文档来源，也可为您提供协助以创建一个咨询工单。'}


def build_qa_graph():  # 将所有节点连接
    g = StateGraph(QAState)  # 创建一个图，此图的状态类型为QAState，图中所有节点的 输入/输出 均基于此状态

    # LangGraph1.0+ 以上版本要求节点名必须是字符串
    # 此处将前述函数变为图中节点
    # 注意: 节点注册用runnable(返回dict)
    g.add_node('decide_retrieve', decide_retrieve_node)
    g.add_node('retrieve', retrieve)
    g.add_node('generate', generate_answer)
    g.add_node('refuse', refuse_of_clarify)

    # 入口，从START->decide_retrieve，图在运行伊始进入的函数
    g.add_edge(START, 'decide_retrieve')

    # decide_retrieve路由，根据decide_retrieve的返回值分流
    # 再次传入decide_retrieve作为'路由函数'
    # 如果它返回retrieve则走到retrieve节点
    # 如果它返回direct则走到generate节点
    # 目前此项目暂时固定返回retrieve
    g.add_conditional_edges(
        'decide_retrieve',
        decide_retrieve,
        {
            'retrieve': 'retrieve',
            'direct': 'generate'
        }
    )

    # retrieve后根据证据充分性 路由(分支选择某条边)
    g.add_conditional_edges(
        'retrieve',
        grade_evidence,
        {
            'good': 'generate',
            'bad': 'refuse'
        }
    )

    # 结束边，无论生成答案或是拒绝，最终都会到END，流程结束
    g.add_edge('generate', END)
    g.add_edge('refuse', END)

    return g.compile()  # 编译成可调用的 graph app

# if __name__ == '__main__':
#     g = build_qa_graph()
#     print(g)