# agent/plan_agent.py

from utils.logger_handler import logger


class PlanAgent:
    """规划智能体 - 金牌规划师，只负责写路书"""

    def __init__(self, llm):
        self.llm = llm

    def draft(self, state: dict) -> dict:
        revision_count = state.get("revision_count", 0)
        user_id = state.get("user_id", "unknown")
        logger.info(f"[PlanAgent] 起草路书 (第 {revision_count + 1} 次)...")

        system_msg = "你是一个金牌旅游规划师。请严格结合事实清单和用户核心档案撰写详细、可执行的旅行路书。"

        user_msg = (
            f"【核心档案(红线)】: {state.get('travel_spec', {})}\n"
            f"【真实意图(目标)】: {state.get('true_intent', '')}\n"
            f"【客观事实(依据)】: {state.get('facts_context', '')}"
        )

        feedback = state.get("feedback", "")
        if feedback:
            user_msg = (
                f"【请针对以下审计意见进行针对性修改】：\n{feedback}\n\n" + user_msg
            )

        try:
            response = self.llm.invoke([
                ("system", system_msg),
                ("user", user_msg),
            ])
            content = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error(f"[PlanAgent] 调用失败: {e}")
            content = "抱歉，路书生成失败，请稍后再试。"

        return {"draft_itinerary": content, "revision_count": revision_count + 1}
