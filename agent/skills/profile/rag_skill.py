# agent/skills/context/rag_skill.py

from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# 引入你写好的底层业务逻辑
from rag.rag_service import RagSummarizeService
'''
只能用来查公共部分的哈，也就是使用了query改写来模糊查询
'''

class RagSkillInput(BaseModel):
    query: str = Field(..., description="专供内部知识库 RAG 检索使用的名词性短语（如：哈尔滨 极地馆 亲子游）")


class RagSkill(BaseTool):
    # 这是大模型呼叫这个工具的唯一暗号，必须叫 rag_summarize
    name: str = "rag_summarize"
    description: str = "【内部知识库检索技能】当需要查询详细的景点攻略、避坑指南、本地口碑推荐时，必须调用此工具。"
    args_schema: Type[BaseModel] = RagSkillInput

    def _run(self, query: str) -> str:
        # 在这里实例化并调用你的具体服务！
        rag_service = RagSummarizeService()
        return rag_service.rag_summarize(query)