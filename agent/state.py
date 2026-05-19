# agent/state.py

from typing import TypedDict, Literal


class TravelState(TypedDict):
    """LangGraph 全局状态字典"""

    # 1. 基础输入信息
    user_id: str
    query: str
    short_term_history: str

    # 2. Gateway 产物
    is_chitchat: bool
    chitchat_reply: str
    intent_type: Literal["chitchat", "tool_only", "planning"]  # 意图类型
    true_intent: str
    rag_keyword: str
    mcp_keyword: str
    tool_name: str  # 工具类意图时，指定要调用的工具名
    tool_args: dict  # 工具类意图时，工具参数

    # 3. 工具类直接输出
    tool_response: str

    # 4. Retriever 产物
    facts_context: str

    # 5. Creator 产物
    draft_itinerary: str
    revision_count: int

    # 6. AuditAgent 产物
    eval_status: Literal["Pass", "Fail", "Pending"]
    feedback: str
    audit_count: int

    # 7. 全局结构化记忆
    travel_spec: dict
