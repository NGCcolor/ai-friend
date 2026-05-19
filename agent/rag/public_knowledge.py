# agent/rag/public_knowledge.py

import time
from agent.rag.base_chroma import BaseChromaDB
from config import settings
from utils.logger_handler import logger


class PublicKnowledgeDB(BaseChromaDB):
    def __init__(self):
        collection_name = settings.chroma.public_collection
        super().__init__(collection_name)
        self.k = settings.chroma.k

    def search_knowledge(self, query: str) -> str:
        logger.info(f"检索公共知识库(含评价): {query}")
        results = self.vector_store.similarity_search(query, k=self.k)
        if not results:
            return "暂无相关的公共攻略或历史真实评价。"
        return "\n".join([f"- {doc.page_content}" for doc in results])

    def add_review(self, target_name: str, rating: float, content: str, user_id: str = "anonymous"):
        review_text = f"【真实游客评价】目标：{target_name} | 评分：{rating}星 | 内容：{content}"
        try:
            self.vector_store.add_texts(
                texts=[review_text],
                metadatas=[{
                    "type": "ugc_review",
                    "target": target_name,
                    "rating": rating,
                    "reviewer_id": user_id,
                    "timestamp": time.time()
                }]
            )
            logger.info(f"成功录入公共评价: {target_name} ({rating}星)")
        except Exception as e:
            logger.error(f"录入公共评价失败: {e}")

    def upload_documents(self, documents):
        self.vector_store.add_documents(documents)
        self.persist()


public_db = PublicKnowledgeDB()