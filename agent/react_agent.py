# agent/react_agent.py

import time
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START
from pydantic import BaseModel, Field
from typing import Literal, Optional

from model.factory import chat_model
from agent.skills.skill_manager import skill_manager
from utils.gateway_handler import IntentGateway
from utils.logger_handler import logger
from agent.state import TravelState

# 引入解耦的三大数据库实例
from agent.rag.history_record import history_db
from agent.rag.user_profile import profile_db
from agent.rag.public_knowledge import public_db


class ReactAgent:
    def __init__(self):
        """初始化基于 LangGraph 的多智能体工作流"""
        self.gateway = IntentGateway(chat_model)
        self.all_tools = skill_manager.get_all_skills()
        self.app = self._build_graph()

    def _build_graph(self):
        """构建核心的状态机图网络"""
        workflow = StateGraph(TravelState)

        workflow.add_node("Gateway", self._node_gateway)
        workflow.add_node("Memory", self._node_memory)
        workflow.add_node("Retriever", self._node_retriever)
        workflow.add_node("Creator", self._node_creator)
        workflow.add_node("Evaluator", self._node_evaluator)

        workflow.add_edge(START, "Gateway")

        def route_after_gateway(state: TravelState):
            if state.get("is_chitchat"):
                return END
            return "Memory"

        workflow.add_conditional_edges("Gateway", route_after_gateway)
        workflow.add_edge("Memory", "Retriever")
        workflow.add_edge("Retriever", "Creator")
        workflow.add_edge("Creator", "Evaluator")

        def route_after_eval(state: TravelState):
            if state["eval_status"] == "Pass":
                return END
            # 设置最大修订次数限制，防止死循环
            if state.get("revision_count", 0) >= 3:
                logger.warning(f"[{state['user_id']}] 触发强制熔断！已达最大修改次数。")
                return END

            return "Creator"

        workflow.add_conditional_edges("Evaluator", route_after_eval)

        return workflow.compile()

    # ==========================================
    # 节点 1: Gateway (网关：意图解析 + 数据实时回写)
    # ==========================================
    def _node_gateway(self, state: TravelState) -> dict:
        logger.info(f"[{state['user_id']}] 进入 Gateway 节点: 意图识别与数据回写...")
        result = self.gateway.process(query=state["query"], history=state["short_term_history"])

        # 闭环：画像实时更新
        if getattr(result, 'has_profile_update', False) and getattr(result, 'extracted_profile', ""):
            profile_db.upsert_profile(user_id=state["user_id"], profile_tag=result.extracted_profile)

        # 闭环：UGC评价回写
        if getattr(result, 'is_review', False) and getattr(result, 'review_target', ""):
            public_db.add_review(
                target_name=result.review_target,
                rating=result.review_rating,
                content=result.review_content,
                user_id=state["user_id"]
            )

        return {
            "is_chitchat": result.is_chitchat,
            "chitchat_reply": result.chitchat_reply,
            "true_intent": result.true_intent,
            "rag_keyword": result.rag_keyword,
            "mcp_keyword": result.mcp_keyword
        }

    # ==========================================
    # 节点 2: Memory (结构化记忆管家：保底线)
    # ==========================================
    class TravelMemory(BaseModel):
        destination: str = Field(default="未知", description="目的地")
        duration: str = Field(default="未知", description="天数")
        companions: str = Field(default="未知", description="同行人")
        budget: str = Field(default="未知", description="预算")
        special_requests: str = Field(default="无", description="忌口、避雷等核心约束")

    def _node_memory(self, state: TravelState) -> dict:
        logger.info(f"[{state['user_id']}] 进入 Memory 节点: 更新 JSON 约束档案...")
        old_spec = state.get("travel_spec", {})
        memory_llm = chat_model.with_structured_output(self.TravelMemory)

        prompt = f"""你是一个严谨的管家。请根据最新输入更新旅游档案。
【旧记忆档案】：{old_spec}
【用户最新输入】：{state['query']}
"""
        new_memory = memory_llm.invoke(prompt)
        memory_dict = new_memory.model_dump() if hasattr(new_memory, 'model_dump') else new_memory.dict()
        return {"travel_spec": memory_dict}

    # ==========================================
    # 节点 3: Retriever (四路并发策略检索)
    # ==========================================
    def _node_retriever(self, state: TravelState) -> dict:
        logger.info(f"[{state['user_id']}] 进入 Retriever 节点: 执行多路策略召回...")
        user_id = state["user_id"]
        rag_keyword = state["rag_keyword"]
        mcp_keyword = state["mcp_keyword"]

        facts_list = []
        # i. 私有画像 (禁用HyDE)
        facts_list.append(f"【专属画像】:\n{profile_db.get_user_profiles(user_id)}")
        # ii. 历史记录 (禁用HyDE)
        facts_list.append(f"【历史偏好】:\n{history_db.recall_history(user_id, rag_keyword)}")
        # iii. 公共攻略 (启用HyDE + 0.8熔断)
        facts_list.append(f"【公共事实与点评】:\n{public_db.search_with_hyde(rag_keyword, 0.8)}")

        # iv. 外部 MCP
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你负责调用外部工具抓取实时动态。"),
            ("user", "辅助检索词：【{mcp_keyword}】"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        agent_executor = AgentExecutor(agent=create_tool_calling_agent(chat_model, self.all_tools, prompt),
                                       tools=self.all_tools)
        mcp_res = agent_executor.invoke({"mcp_keyword": mcp_keyword})

        return {"facts_context": "\n\n".join(facts_list) + f"\n\n【外部动态】:\n{mcp_res['output']}"}

    # ==========================================
    # 节点 4: Creator (基于反馈的起草者)
    # ==========================================
    def _node_creator(self, state: TravelState) -> dict:
        revision_count = state.get("revision_count", 0)
        logger.info(f"[{state['user_id']}] 起草路书 (第 {revision_count + 1} 次)...")

        system_msg = "你是一个金牌规划师。请严格结合事实清单和JSON红线撰写详细路书。"
        user_msg = f"""【核心档案(红线)】: {state['travel_spec']}
【真实意图(目标)】: {state['true_intent']}
【客观事实(依据)】: {state['facts_context']}"""

        # 🌟 关键：如果有质检建议，强行喂给 Creator
        if state.get("feedback"):
            user_msg = f"🚨【请针对以下审查意见进行针对性修改】：\n{state['feedback']}\n\n" + user_msg

        response = chat_model.invoke([("system", system_msg), ("user", user_msg)])
        return {"draft_itinerary": response.content, "revision_count": revision_count + 1}

    # ==========================================
    # 节点 5: 升级版 Evaluator (资深质检审计官)
    # ==========================================
    class EvalResult(BaseModel):
        status: Literal["Pass", "Fail"] = Field(description="审查结论")
        error_type: Optional[Literal["红线违规", "意图偏离", "事实错误"]] = Field(description="错误分类")
        audit_report: str = Field(description="详细的问题描述")
        suggestions: str = Field(description="给规划师的具体修改建议，需具体到操作层面")

    def _node_evaluator(self, state: TravelState) -> dict:
        logger.info(f"[{state['user_id']}] 进入质检审计节点...")
        eval_llm = chat_model.with_structured_output(self.EvalResult)

        prompt = f"""你是一个极度苛刻的旅游质量审计员。请对比以下三项内容审计【草稿路书】：
1. 【JSON红线】：{state.get('travel_spec')} (必须死守，如预算、忌口)
2. 【用户目标】：{state['true_intent']} (风格、情绪、隐性需求必须对齐)
3. 【事实依据】：{state['facts_context']} (时间、地点、价格必须真实)

【草稿内容】：
{state['draft_itinerary']}

你的任务：
- 找出路书与红线冲突的地方。
- 找出路书与用户目标不符的地方（如：用户想散心，你安排了特种兵行程）。
- 找出路书与客观事实矛盾的地方。
若不完美，必须Fail并给出具体建议。
"""
        result = eval_llm.invoke(prompt)

        feedback_msg = ""
        if result.status == "Fail":
            feedback_msg = f"【错误类型】: {result.error_type}\n【审计报告】: {result.audit_report}\n【专家建议】: {result.suggestions}"
            logger.warning(f"质检未通过: {result.audit_report}")

        return {"eval_status": result.status, "feedback": feedback_msg}

    # ==========================================
    # 流式接口 (双轨闭环)
    # ==========================================
    def execute_stream(self, query: str, user_id: str = "default_user", short_term_history: str = ""):
        history_db.add_log(user_id=user_id, role="user", content=query)

        initial_state = {
            "query": query, "user_id": user_id, "short_term_history": short_term_history,
            "revision_count": 0, "travel_spec": {}
        }

        current_draft = ""
        for event in self.app.stream(initial_state, {"recursion_limit": 15}):
            for node_name, state_update in event.items():
                if node_name == "Creator":
                    current_draft = state_update.get("draft_itinerary", "")

                if node_name == "Gateway" and state_update.get("is_chitchat"):
                    reply = state_update["chitchat_reply"]
                    history_db.add_log(user_id, "assistant", reply)
                    yield reply
                    return

                if node_name == "Evaluator" and state_update.get("eval_status") == "Pass":
                    history_db.add_log(user_id, "assistant", current_draft)
                    proactive_ask = "\n\n---\n💡 **AI管家**: 路书已备好！体验完回来记得回复“XX景点很坑/很赞”哦，我会记入避坑指南！"
                    yield current_draft + proactive_ask
                    return