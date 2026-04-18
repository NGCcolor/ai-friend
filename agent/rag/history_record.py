# agent/rag/history_record.py

import time
from agent.rag.base_chroma import BaseChromaDB
from utils.config_handler import chroma_conf  # 使用你的 chroma_conf
from utils.logger_handler import logger

class HistoryRecordDB(BaseChromaDB):
    def __init__(self):
        collection_name = chroma_conf.get("history_collection_name", "travel_history_records")
        super().__init__(collection_name)

    def add_log(self, user_id: str, role: str, content: str):
        """追加一条聊天记录到向量库"""
        try:
            self.vector_store.add_texts(
                texts=[f"[{role}的原话]: {content}"],
                metadatas=[{
                    "user_id": user_id,
                    "type": "chat_history",
                    "role": role,
                    "timestamp": time.time()
                }]
            )
        except Exception as e:
            logger.error(f"[{user_id}] 写入历史向量库失败: {e}")

    def recall_history(self, user_id: str, query: str, k: int = 5) -> str:
        """召回该用户相关的历史原话"""
        results = self.vector_store.similarity_search(
            query=query,
            k=k,
            filter={"user_id": user_id, "type": "chat_history"} # 强隔离
        )
        if not results:
            return ""
        return "\n".join([doc.page_content for doc in results])

# 全局单例
history_db = HistoryRecordDB()