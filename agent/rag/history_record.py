# agent/rag/history_record.py

import time
from agent.rag.base_chroma import BaseChromaDB
from config import settings
from utils.logger_handler import logger


class HistoryRecordDB(BaseChromaDB):
    def __init__(self):
        collection_name = settings.chroma.history_collection
        super().__init__(collection_name)

    def add_log(self, user_id: str, role: str, content: str):
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
        results = self.vector_store.similarity_search(
            query=query,
            k=k,
            filter={"$and": [{"user_id": user_id}, {"type": "chat_history"}]}
        )
        if not results:
            return ""
        return "\n".join([doc.page_content for doc in results])


history_db = HistoryRecordDB()