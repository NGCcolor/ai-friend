# agent/rag/user_profile.py

from agent.rag.base_chroma import BaseChromaDB
from config import settings
from utils.logger_handler import logger


class UserProfileDB(BaseChromaDB):
    def __init__(self):
        collection_name = settings.chroma.profile_collection
        super().__init__(collection_name)

    def upsert_profile(self, user_id: str, profile_tag: str):
        self.vector_store.add_texts(
            texts=[profile_tag],
            metadatas=[{"user_id": user_id, "type": "profile"}]
        )
        logger.info(f"[{user_id}] 已记录画像标签: {profile_tag}")

    def get_user_profiles(self, user_id: str) -> str:
        results = self.vector_store.similarity_search(
            query="用户的核心旅游偏好、忌口、住宿要求",
            k=5,
            filter={"$and": [{"user_id": user_id}, {"type": "profile"}]}
        )
        if not results:
            return "暂无该用户的特殊画像标签。"
        return "\n".join([doc.page_content for doc in results])


profile_db = UserProfileDB()