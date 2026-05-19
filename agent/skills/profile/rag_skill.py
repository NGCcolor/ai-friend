# agent/skills/profile/rag_skill.py

from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from rag.rag_service import RagSummarizeService


class RagSkillInput(BaseModel):
    query: str = Field(..., description="专供内部知识库 RAG 检索使用的名词性短语（如：哈尔滨 极地馆 亲子游）")


class RagSkill(BaseTool):
    name: str = "rag_summarize"
    description: str = "【内部知识库检索技能】当需要查询详细的景点攻略、避坑指南、本地口碑推荐时，必须调用此工具。"
    args_schema: Type[BaseModel] = RagSkillInput

    def _run(self, query: str) -> str:
        rag_service = RagSummarizeService()
        return rag_service.rag_summarize(query)