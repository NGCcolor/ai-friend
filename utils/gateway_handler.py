# utils/gateway_handler.py

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from utils.logger_handler import logger


# 1. 扩充输出结构：增加画像和评价字段
class GatewayOutput(BaseModel):
    is_chitchat: bool = Field(description="是否是打招呼、闲聊，或者单纯的游后评价反馈。")
    chitchat_reply: str = Field(description="如果是闲聊或评价，给出的回复。")
    true_intent: str = Field(description="如果是需要规划路书，提取的真实意图。")
    rag_keyword: str = Field(description="内部知识库的检索关键词。")
    mcp_keyword: str = Field(description="外部小红书的检索关键词。")

    # 【新增】：CQRS 数据回流字段
    has_profile_update: bool = Field(default=False, description="用户是否提及了长期的个人偏好、忌口等")
    extracted_profile: str = Field(default="", description="如果提及偏好，提取出的具体内容，如'海鲜过敏'")
    is_review: bool = Field(default=False, description="用户是否在提供景点/路线的游后真实评价或避坑")
    review_target: str = Field(default="", description="评价的具体景点或对象，如'冰雪大世界'")
    review_rating: float = Field(default=5.0, description="推测的评价星级(1.0-5.0)")
    review_content: str = Field(default="", description="评价的具体避坑/推荐内容")


class IntentGateway:
    def __init__(self, llm):
        self.structured_llm = llm.with_structured_output(GatewayOutput)

        # 2. 升级 Prompt，注入评价拦截规则
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个企业级旅游 AI 管家的前置智能网关与 Query 改写引擎。
你的核心任务是：意图识别、提取画像/评价，并生成高纯度的检索词。

【执行规则】：
1. 指代消解：严格结合【历史对话】，推断用户最新输入中的代词指代什么。
2. 闲聊拦截：如果是打招呼，无需改写，直接在 chitchat_reply 生成回复，is_chitchat=True。
3. 画像提取：如果用户提到了长期偏好（如“我以后都不吃辣”、“穷游党”），将其提取到 extracted_profile，has_profile_update=True。
4. 🌟评价拦截（极其重要）：如果用户是在反馈游玩体验（如“昨天去的亚特兰蒂斯太坑了排队好久”）：
   - 将 is_review 设为 True，提取评价目标、评分和内容。
   - 必须将 is_chitchat 设为 True！（因为只需记录反馈，无需做新规划）。
   - 在 chitchat_reply 中热心地感谢用户的反馈，并告知已记录到避坑指南。

【当前用户画像标签】：{user_profile_tags}
【历史对话记录】：\n{history}"""),
            ("user", "用户最新输入：{query}")
        ])

    def process(self, query: str, history: str = "无历史对话", user_profile_tags: str = ""):
        logger.info(f"[IntentGateway] 正在对输入进行意图分析与改写: {query}")
        chain = self.prompt | self.structured_llm
        try:
            return chain.invoke({
                "query": query,
                "history": history[-500:],  # 截断防止 token 爆炸
                "user_profile_tags": user_profile_tags
            })
        except Exception as e:
            logger.error(f"[IntentGateway] 网关解析失败: {e}")
            return GatewayOutput(
                is_chitchat=False, chitchat_reply="",
                true_intent=query, rag_keyword=query, mcp_keyword=query
            )