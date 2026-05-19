# agent/react_agent.py

import json
import re
import time
from pydantic import BaseModel, Field
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from model.factory import chat_model
from agent.skills.skill_manager import skill_manager
from utils.gateway_handler import IntentGateway
from utils.logger_handler import logger
from agent.state import TravelState
from agent.plan_agent import PlanAgent
from agent.audit_agent import AuditAgent

from agent.rag.history_record import history_db
from agent.rag.user_profile import profile_db
from agent.rag.public_knowledge import public_db


def retry_tool_call(func, args=None, max_retries=2):
    """工具调用重试机制"""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return func(args or {})
        except Exception as e:
            last_error = e
            logger.warning(f"工具调用失败 (第{attempt + 1}次): {e}")
            if attempt < max_retries:
                time.sleep(0.5)
    raise last_error


class ReactAgent:
    def __init__(self):
        self.gateway = IntentGateway(chat_model)
        self.all_tools = skill_manager.get_all_skills()
        self.plan_agent = PlanAgent(chat_model)
        self.audit_agent = AuditAgent(chat_model)
        self.app = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(TravelState)

        # 添加节点
        workflow.add_node("Gateway", self._node_gateway)
        workflow.add_node("ToolExecutor", self._node_tool_executor)
        workflow.add_node("Memory", self._node_memory)
        workflow.add_node("Retriever", self._node_retriever)
        workflow.add_node("PlanAgent", self.plan_agent.draft)
        workflow.add_node("AuditAgent", self.audit_agent.audit)

        # 起点
        workflow.add_edge(START, "Gateway")

        # Gateway 后的路由
        def route_after_gateway(state: TravelState):
            intent_type = state.get("intent_type", "planning")
            if intent_type == "chitchat":
                return END
            elif intent_type == "tool_only":
                return "ToolExecutor"
            else:
                return "Memory"

        workflow.add_conditional_edges("Gateway", route_after_gateway)
        workflow.add_edge("ToolExecutor", END)
        workflow.add_edge("Memory", "Retriever")
        workflow.add_edge("Retriever", "PlanAgent")
        workflow.add_edge("PlanAgent", "AuditAgent")

        # AuditAgent 后的路由：Pass 或 熔断 → END，Fail → 回到 PlanAgent
        def route_after_audit(state: TravelState):
            if state["eval_status"] == "Pass":
                return END
            if state.get("revision_count", 0) >= 2 or state.get("audit_count", 0) >= 2:
                logger.warning(f"[{state['user_id']}] 触发强制熔断！")
                return END
            return "PlanAgent"

        workflow.add_conditional_edges("AuditAgent", route_after_audit)
        return workflow.compile()

    # ==========================================
    # 节点 1: Gateway
    # ==========================================
    def _node_gateway(self, state: TravelState) -> dict:
        logger.info(f"[{state['user_id']}] 进入 Gateway 节点...")
        result = self.gateway.process(query=state["query"], history=state["short_term_history"])

        # 画像实时更新
        if getattr(result, 'has_profile_update', False) and getattr(result, 'extracted_profile', ""):
            profile_db.upsert_profile(user_id=state["user_id"], profile_tag=result.extracted_profile)

        # UGC评价回写
        if getattr(result, 'is_review', False) and getattr(result, 'review_target', ""):
            public_db.add_review(
                target_name=result.review_target,
                rating=result.review_rating,
                content=result.review_content,
                user_id=state["user_id"]
            )

        return {
            "intent_type": result.intent_type,
            "is_chitchat": result.intent_type == "chitchat",
            "chitchat_reply": result.chitchat_reply,
            "true_intent": result.true_intent,
            "rag_keyword": result.rag_keyword,
            "mcp_keyword": result.mcp_keyword,
            "tool_name": result.tool_name,
            "tool_args": result.tool_args,
        }

    # ==========================================
    # 节点 2: ToolExecutor
    # ==========================================
    def _node_tool_executor(self, state: TravelState) -> dict:
        logger.info(f"[{state['user_id']}] 进入 ToolExecutor 节点...")
        tool_name = state.get("tool_name", "")
        tool_args = state.get("tool_args", {})

        if not tool_name:
            return {"chitchat_reply": "抱歉，无法识别您需要的工具。"}

        target_tool = next((t for t in self.all_tools if t.name == tool_name), None)
        if not target_tool:
            return {"chitchat_reply": f"抱歉，工具 {tool_name} 不存在。"}

        try:
            response = retry_tool_call(target_tool.invoke, args=tool_args, max_retries=2)
            chitchat_reply = f"好的，为您查询到：\n\n{response}"
            history_db.add_log(state["user_id"], "assistant", chitchat_reply)
            return {"chitchat_reply": chitchat_reply}
        except Exception as e:
            logger.error(f"[{state['user_id']}] 工具执行最终失败: {e}")
            return {"chitchat_reply": "抱歉，服务暂时不可用，请稍后再试。"}

    # ==========================================
    # 节点 3: Memory
    # ==========================================
    def _node_memory(self, state: TravelState) -> dict:
        class TravelMemory(BaseModel):
            destination: str = Field(default="未知", description="目的地")
            duration: str = Field(default="未知", description="天数")
            companions: str = Field(default="未知", description="同行人")
            budget: str = Field(default="未知", description="预算")
            special_requests: str = Field(default="无", description="忌口、避雷等核心约束")

        logger.info(f"[{state['user_id']}] 进入 Memory 节点...")
        old_spec = state.get("travel_spec", {})
        user_id = state["user_id"]

        user_profile = profile_db.get_user_profiles(user_id)
        logger.info(f"[{user_id}] 读取到用户画像: {user_profile[:100]}...")

        prompt = f"""你是一个严谨的管家。请根据以下信息更新旅游档案。

【用户长期画像】：{user_profile}
【旧记忆档案】：{old_spec}
【用户最新输入】：{state['query']}

注意：必须将用户长期画像中的偏好（忌口、体力、预算等）整合到档案中。

请严格按照以下JSON格式返回：
{{"destination": "目的地", "duration": "天数", "companions": "同行人", "budget": "预算", "special_requests": "整合忌口、避雷等约束"}}
"""
        try:
            memory_llm = chat_model.with_structured_output(TravelMemory)
            new_memory = memory_llm.invoke(prompt)
            memory_dict = new_memory.model_dump() if hasattr(new_memory, 'model_dump') else new_memory.dict()
            return {"travel_spec": memory_dict}
        except Exception as e:
            logger.warning(f"[{user_id}] Memory节点JSON解析失败: {e}")
            try:
                response = chat_model.invoke(prompt)
                content = response.content if hasattr(response, 'content') else str(response)
                json_match = re.search(r'\{[^{}]+\}', content, re.DOTALL)
                if json_match:
                    memory_dict = json.loads(json_match.group())
                    return {"travel_spec": memory_dict}
            except Exception as e2:
                logger.error(f"[{user_id}] 手动提取JSON也失败: {e2}")
            return {"travel_spec": old_spec}

    # ==========================================
    # 节点 4: Retriever
    # ==========================================
    def _node_retriever(self, state: TravelState) -> dict:
        logger.info(f"[{state['user_id']}] 进入 Retriever 节点...")
        user_id = state["user_id"]
        rag_keyword = state["rag_keyword"]
        mcp_keyword = state.get("mcp_keyword", "")

        facts_list = []
        facts_list.append(f"【专属画像】:\n{profile_db.get_user_profiles(user_id)}")
        facts_list.append(f"【历史偏好】:\n{history_db.recall_history(user_id, rag_keyword)}")
        facts_list.append(f"【公共事实与点评】:\n{public_db.search_knowledge(rag_keyword)}")

        external_info = ""
        if mcp_keyword:
            try:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """你是旅游信息助手。根据用户需求调用合适的工具获取实时信息。
可用工具：天气查询、时间感知、定位感知等。
请根据关键词判断需要调用哪个工具，并传入正确参数。"""),
                    ("user", "需要查询的信息：{keyword}"),
                    ("placeholder", "{agent_scratchpad}"),
                ])
                agent = create_tool_calling_agent(chat_model, self.all_tools, prompt)
                agent_executor = AgentExecutor(agent=agent, tools=self.all_tools, max_iterations=3, verbose=False)
                mcp_res = agent_executor.invoke({"keyword": mcp_keyword})
                external_info = f"\n\n【外部动态】:\n{mcp_res.get('output', '')}"
            except Exception as e:
                logger.warning(f"外部工具调用失败: {e}")

        return {"facts_context": "\n\n".join(facts_list) + external_info}

    # ==========================================
    # 流式接口
    # ==========================================
    def execute_stream(self, query: str, user_id: str = "default_user", short_term_history: str = ""):
        history_db.add_log(user_id=user_id, role="user", content=query)

        initial_state = {
            "query": query,
            "user_id": user_id,
            "short_term_history": short_term_history,
            "revision_count": 0,
            "audit_count": 0,
            "travel_spec": {},
            "intent_type": "planning",
            "tool_name": "",
            "tool_args": {},
        }

        current_draft = ""
        for event in self.app.stream(initial_state, {"recursion_limit": 15}):
            for node_name, state_update in event.items():
                if node_name == "Gateway" and state_update.get("is_chitchat"):
                    reply = state_update.get("chitchat_reply", "")
                    history_db.add_log(user_id, "assistant", reply)
                    yield reply
                    return

                if node_name == "ToolExecutor":
                    reply = state_update.get("chitchat_reply", "")
                    yield reply
                    return

                if node_name == "PlanAgent":
                    current_draft = state_update.get("draft_itinerary", "")

                if node_name == "AuditAgent" and state_update.get("eval_status") == "Pass":
                    history_db.add_log(user_id, "assistant", current_draft)
                    yield current_draft + "\n\n---\n**AI管家**: 路书已备好！体验完回来记得告诉我感受，我会记入避坑指南！"
                    return

        # 熔断兜底：如果循环结束仍未 Pass，输出最后一版
        if current_draft:
            history_db.add_log(user_id, "assistant", current_draft)
            yield current_draft
