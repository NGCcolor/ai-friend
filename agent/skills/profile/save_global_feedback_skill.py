import time
import hashlib
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from rag.vector_store import VectorStoreService
from utils.logger_handler import logger

# 实例化全局旅游知识库（与用户画像库隔离）
knowledge_vs = VectorStoreService(collection_name="travel_knowledge_base")


class FeedbackInput(BaseModel):
    location_name: str = Field(..., description="景点、美食或餐厅的名称")
    rating_label: str = Field(..., description="评分级别：拉完了(0), npc(1), 人上人(2), 顶尖(3), 夯(5)")
    score: int = Field(..., description="具体的数字分数（0, 1, 2, 3, 5）")
    comment: str = Field(..., description="用户的具体评价内容缩影")


class SaveGlobalFeedbackSkill(BaseTool):
    name: str = "save_global_feedback_skill"
    description: str = "【全局进化技能】将用户对特定地点的评分和评价存入公共知识库。用于丰富 RAG 资料库，影响未来所有用户的推荐策略。"
    args_schema: Type[BaseModel] = FeedbackInput

    def _run(self, location_name: str, rating_label: str, score: int, comment: str) -> str:
        # 生成唯一ID，允许同一个景点有多条不同用户的评价
        unique_str = f"{location_name}_{time.time()}"
        doc_id = f"feedback_{hashlib.md5(unique_str.encode()).hexdigest()[:10]}"

        # 构造存入 RAG 的自然语言文本（方便语义检索）
        content = f"关于【{location_name}】的用户真实评价：体验级别为「{rating_label}」（{score}分）。用户反馈详情：{comment}。"

        # 元数据用于精准过滤
        metadata = {
            "type": "user_feedback",
            "location": location_name,
            "score": score,
            "label": rating_label
        }

        try:
            knowledge_vs.upsert_text(doc_id=doc_id, text=content, metadata=metadata)
            logger.info(f"成功存入【{location_name}】的全局反馈：{rating_label}")
            return f"✅ 全局知识库已更新：【{location_name}】的 {score}分({rating_label}) 评价已纳入系统参考池。"
        except Exception as e:
            logger.error(f"存入全局反馈失败: {e}")
            return "❌ 反馈存入知识库失败。"