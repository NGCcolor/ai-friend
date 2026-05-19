from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from rag.vector_store import VectorStoreService
from utils.logger_handler import logger
from config import settings

profile_collection = settings.chroma.profile_collection
profile_vector_store = VectorStoreService(collection_name=profile_collection)


# =======================================================
# 技能 1：基于强契约模板提取并保存画像 (企业级进阶版)
# =======================================================
class UpdateProfileInput(BaseModel):
    """
    通过强类型 Field 约束，逼迫大模型必须思考并提取这些具体维度。
    即使有些信息用户没说，大模型也必须显式填入“未知”，这样能有效防止关键维度遗漏。
    """
    user_id: str = Field(..., description="用户的唯一ID，如 '1001'")

    # 结构化填表区
    dietary: str = Field(default="未知",
                         description="饮食偏好与忌口，如：不吃香菜、海鲜过敏、无辣不欢。若对话中未提及则填'未知'")
    pace: str = Field(default="未知",
                      description="旅行节奏与体力：如 特种兵、休闲度假、带娃慢游、不愿走路。若未提及则填'未知'")
    budget: str = Field(default="未知", description="消费预期：如 穷游、极致性价比、轻奢、不在乎钱。若未提及则填'未知'")
    avoid: str = Field(default="无", description="绝对避雷项(极其重要)：如 讨厌排队、拒绝爬山、不早起。若无则填'无'")

    # 自然语言区
    ai_summary: str = Field(..., description="结合上述标签，对用户写一段自然语言的综合描述，用于语义搜索。")
    tags_str: str = Field(..., description="核心标签集合，用逗号分隔，如：'怕冷,博物馆控,低体力'")


class UpdateUserProfileSkill(BaseTool):
    name: str = "update_user_profile_skill"
    description: str = "【画像更新技能】当用户在对话中表达了偏好，调用此技能提取并结构化保存用户的长期画像。"
    args_schema: Type[BaseModel] = UpdateProfileInput

    def _run(self, user_id: str, dietary: str, pace: str, budget: str, avoid: str, ai_summary: str,
             tags_str: str) -> str:
        # 1. 组装结构化的 Metadata（元数据）
        # 这样做的好处是：以后你想在数据库里硬性筛选 "预算=穷游" 的用户时，极其方便！
        structured_metadata = {
            "user_id": user_id,
            "type": "user_profile",
            "tags": tags_str,
            "dietary": dietary,
            "pace": pace,
            "budget": budget,
            "avoid": avoid
        }

        # 2. 组装存入 Page_Content 的自然语言文本
        # 我们把结构化数据再拼装成极具语义丰富的文本，为了以后能被“我想找个安静地方发呆(FindSimilarVibe)”这种模糊搜索精准搜到
        rich_content = f"""
【用户综合画像】：{ai_summary}
【饮食忌口】：{dietary}
【旅行节奏】：{pace}
【消费预期】：{budget}
【绝对避雷】：{avoid}
"""

        # 3. 存入底层向量库
        success = profile_vector_store.upsert_text(
            doc_id=str(user_id),
            text=rich_content.strip(),
            metadata=structured_metadata
        )

        if success:
            logger.info(f"[画像更新] 成功保存用户 {user_id} 的结构化模板画像。")
            return f"✅ 用户 {user_id} 的画像已成功提取并结构化存入私有记忆库！"
        return "❌ 画像存储失败。"


# =======================================================
# 技能 2：读取特定用户的私有画像
# =======================================================
class GetProfileInput(BaseModel):
    user_id: str = Field(..., description="用户的唯一ID")


class GetUserProfileSkill(BaseTool):
    name: str = "get_user_profile_skill"
    description: str = "【画像读取技能】直接根据用户ID获取该用户的长期偏好、忌口和体力情况。在规划开始前必须调用，以确保推荐符合用户个性化需求。"
    args_schema: Type[BaseModel] = GetProfileInput

    def _run(self, user_id: str) -> str:
        logger.info(f"[{self.name}] 正在尝试精准读取用户 {user_id} 的长期画像...")

        try:
            # 【企业级核心】：利用你写的 kwargs 透传机制，通过 metadata 精确拦截特定用户！绝对不查别人！
            retriever = profile_vector_store.get_retriever(
                search_kwargs={
                    "k": 1,
                    "filter": {"user_id": user_id}  # 魔法在这里：数据库层面的硬拦截
                }
            )

            # 随便搜个词触发检索，底层会被 filter 死死拦住，只返回 user_id 匹配的那一条
            docs = retriever.invoke("用户的饮食偏好与旅游习惯")

            if docs:
                content = docs[0].page_content
                tags = docs[0].metadata.get("tags", "无标签")
                logger.info(f"[{self.name}] 成功获取用户 {user_id} 画像")
                return f"成功获取用户 ID 为 {user_id} 的历史画像：\n【核心描述】：{content}\n【画像标签】：{tags}"

            logger.info(f"[{self.name}] 未找到用户 {user_id} 的历史记录")
            return f"未找到用户 {user_id} 的历史画像记录。该用户可能是首次使用或尚未建立长期偏好，请基于通用高分逻辑进行推荐。"

        except Exception as e:
            logger.error(f"[{self.name}] 读取画像异常: {str(e)}")
            return f"读取用户画像时出错，请暂时作为新用户处理。"


# =======================================================
# 技能 3：寻找相似老用户的灵魂发问（公共启发）
# =======================================================
class FindSimilarVibeInput(BaseModel):
    vibe_description: str = Field(..., description="用户用自然语言描述的需求，如：'想找个人少安静的地方发呆'")


class FindSimilarVibeSkill(BaseTool):
    name: str = "find_similar_vibe_skill"
    description: str = "【画像检索技能】当需要为用户构思路线时，通过用户的模糊需求去向量库检索历史上有相似偏好的老用户记录，以此获取排雷和推荐灵感。"
    args_schema: Type[BaseModel] = FindSimilarVibeInput

    def _run(self, vibe_description: str) -> str:
        # 这里不需要 filter，因为就是要全库模糊搜索找相似的老铁
        similar_docs = profile_vector_store.similarity_search(query=vibe_description, k=2)

        if not similar_docs:
            return "未在数据库中找到相似偏好的历史记录，请直接发挥创意生成路线。"

        result_texts = []
        for i, doc in enumerate(similar_docs):
            tags = doc.metadata.get("tags", "无标签")
            result_texts.append(f"相似画像 {i + 1} (标签: {tags})：{doc.page_content}")

        return "成功检索到具备相似灵魂特征的历史用户画像：\n" + "\n".join(result_texts)