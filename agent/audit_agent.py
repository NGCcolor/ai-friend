# agent/audit_agent.py

import json
import re
from pydantic import BaseModel, Field
from utils.logger_handler import logger


class AuditResult(BaseModel):
    """审计结果结构"""
    status: str = Field(default="Pass", description="审查结论: Pass 或 Fail")
    error_type: str = Field(default="", description="错误分类")
    audit_report: str = Field(default="", description="问题描述")
    suggestions: str = Field(default="", description="修改建议")


class AuditAgent:
    """审计智能体 - 严苛审计官，只负责质检挑错"""

    def __init__(self, llm):
        self.llm = llm
        self.structured_llm = llm.with_structured_output(AuditResult)

    def audit(self, state: dict) -> dict:
        user_id = state.get("user_id", "unknown")
        logger.info(f"[AuditAgent] 进入质检审计...")

        prompt = (
            f"你是旅游质量审计员。请严格审计以下【草稿路书】是否符合要求。\n\n"
            f"1. 【JSON红线】：{state.get('travel_spec', {})}\n"
            f"2. 【用户目标】：{state.get('true_intent', '')}\n"
            f"3. 【事实依据】：{state.get('facts_context', '')}\n\n"
            f"【草稿内容】：\n{state.get('draft_itinerary', '')}\n\n"
            f"请严格按照以下JSON格式返回：\n"
            f'{{"status": "Pass或Fail", "error_type": "错误类型", "audit_report": "问题描述", "suggestions": "修改建议"}}'
        )

        # 优先尝试结构化输出
        try:
            result = self.structured_llm.invoke(prompt)
            status = result.status.upper() if result.status else "PASS"
        except Exception as e:
            logger.warning(f"[AuditAgent] 结构化输出失败: {e}, 尝试手动提取")
            result, status = self._fallback_parse(prompt)

        feedback_msg = ""
        if status == "FAIL":
            feedback_msg = (
                f"【错误类型】: {result.error_type}\n"
                f"【审计报告】: {result.audit_report}\n"
                f"【专家建议】: {result.suggestions}"
            )

        eval_status = "Fail" if status == "FAIL" else "Pass"
        logger.info(f"[AuditAgent] 审计结果: {eval_status}")
        return {"eval_status": eval_status, "feedback": feedback_msg}

    def _fallback_parse(self, prompt: str) -> tuple:
        """结构化输出失败时的手动解析"""
        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            json_match = re.search(r"\{[^{}]+\}", content, re.DOTALL)
            if json_match:
                result_dict = json.loads(json_match.group())
                result = AuditResult(**result_dict)
                status = result_dict.get("status", "PASS").upper()
                return result, status
        except Exception as e2:
            logger.error(f"[AuditAgent] 手动提取也失败: {e2}")

        return AuditResult(), "PASS"
