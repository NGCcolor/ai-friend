# agent/state.py

from typing import TypedDict, Literal

class TravelState(TypedDict):
    """
    LangGraph 全局状态字典。
    像传送带一样，在 Gateway -> Retriever -> Creator -> Evaluator 之间传递数据。
    """
    # 1. 基础输入信息
    user_id: str
    query: str
    short_term_history: str

    # 2. Gateway (网关) 产物
    is_chitchat: bool
    chitchat_reply: str
    true_intent: str
    rag_keyword: str
    mcp_keyword: str

    # 3. Retriever (数据挖掘机) 产物
    facts_context: str

    # 4. Creator (主规划师) 产物
    draft_itinerary: str
    revision_count: int  # 记录被打回修改的次数，防止死循环

    # 5. Evaluator (质检员) 产物
    eval_status: Literal["Pass", "Fail", "Pending"]
    feedback: str        # 打回时的修改建议

    # 【新增】：全局结构化记忆黑板！
    travel_spec: dict