# agent/skills/profile/history_record_skill.py

from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from rag.vector_store import VectorStoreService
from utils.logger_handler import logger
from utils.config_handler import chroma_conf

# =======================================================
# 实例化独立的【历史记录向量库】
# =======================================================
history_collection = chroma_conf.get("history_collection_name", "travel_history_records")
history_vector_store = VectorStoreService(collection_name=history_collection)


class GetHistoryInput(BaseModel):
    user_id: str = Field(..., description="用户的唯一ID")
    query: str = Field(..., description="需要回溯的历史话题关键词，如：'上一次在哈尔滨住的酒店'")


class GetHistoryRecordSkill(BaseTool):
    name: str = "get_history_record_skill"
    description: str = "【长期记忆读取技能】当用户提到'上次'、'老规矩'、'之前那家'等指代历史上下文的词汇时，调用此工具查阅用户过去生成的专属路书和聊天记录。"
    args_schema: Type[BaseModel] = GetHistoryInput

    def _run(self, user_id: str, query: str) -> str:
        logger.info(f"[{self.name}] 正在为用户 {user_id} 检索历史记忆，关键词: {query}")

        try:
            # 【核心魔法】：普通的 RAG 检索 + 绝对精准的 user_id 物理隔离拦截！
            retriever = history_vector_store.get_retriever(
                search_kwargs={
                    "k": 3,
                    "filter": {"user_id": user_id}  # 铁壁防御：绝对不会把别人的聊天记录拉出来
                }
            )

            docs = retriever.invoke(query)

            if docs:
                context = "\n".join([f"历史片段 {i + 1}: {doc.page_content}" for i, doc in enumerate(docs)])
                logger.info(f"[{self.name}] 成功唤醒用户 {user_id} 的历史记忆")
                return f"成功检索到用户 {user_id} 的专属历史记忆：\n{context}"

            return f"未检索到用户 {user_id} 关于 '{query}' 的历史记录，请直接询问用户具体细节。"

        except Exception as e:
            logger.error(f"[{self.name}] 检索历史记忆异常: {str(e)}")
            return "记忆系统读取异常，暂无历史参考。"