# utils/gateway_handler.py

from pydantic import BaseModel, Field
from typing import Literal, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from utils.logger_handler import logger


class GatewayOutput(BaseModel):
    """网关输出结构"""
    intent_type: Literal["chitchat", "tool_only", "planning"] = Field(
        description="意图类型：chitchat=闲聊, tool_only=纯工具调用, planning=旅游规划"
    )
    chitchat_reply: str = Field(default="", description="闲聊回复，必须结合历史上下文")
    true_intent: str = Field(default="", description="真实意图，结合历史补全指代")
    rag_keyword: str = Field(default="", description="内部知识库检索关键词")
    mcp_keyword: str = Field(default="", description="外部检索关键词")

    # 工具类意图相关
    tool_name: str = Field(default="", description="工具类意图时，指定工具名")
    tool_args: Dict[str, Any] = Field(default={}, description="工具类意图时，工具参数")

    # 画像/评价回流
    has_profile_update: bool = Field(default=False, description="是否更新画像")
    extracted_profile: str = Field(default="", description="提取的画像内容")
    is_review: bool = Field(default=False, description="是否是评价")
    review_target: str = Field(default="", description="评价目标")
    review_rating: float = Field(default=5.0, description="评价星级")
    review_content: str = Field(default="", description="评价内容")


class IntentGateway:
    def __init__(self, llm):
        self.structured_llm = llm.with_structured_output(GatewayOutput)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是旅游AI管家的前置智能网关。你的核心职责是：利用历史对话理解用户真实意图。

【核心原则】：短期记忆是你的大脑！必须结合历史对话处理所有场景！

【意图分类规则】：
1. **chitchat**：打招呼、闲聊、评价反馈
   - 回复时必须结合历史上下文，理解"那里"、"那个地方"、"上次说的"等指代
   - 示例：用户之前聊了哈尔滨，现在说"那里冷吗"→ 回复要提到哈尔滨

2. **tool_only**：纯工具调用（天气、时间、定位）
   - 必须从历史对话补全所有参数！
   - 示例：用户之前说"我在北京"，现在说"明天天气" → tool_args={"city": "北京"}

3. **planning**：旅游规划需求
   - true_intent 要结合历史补全完整意图
   - 示例：用户之前说"想去哈尔滨"，现在说"帮我规划3天" → true_intent="哈尔滨3天旅游规划"

【可用工具及参数】：
- weather_query_skill: {"city": "城市名"} - 查天气
- time_perception_skill: {} - 查时间（无参数）
- location_perception_skill: {} - 查定位（无参数）

【历史对话使用规则】：
1. 指代消解："那里"→具体地点，"明天"→具体日期，"那个"→具体事物
2. 参数补全：如果当前输入缺少信息，必须从历史中提取
3. 上下文连贯：回复要体现你记得之前的对话

【当前用户画像标签】：{user_profile_tags}
【历史对话记录（必须仔细阅读）】：
{history}"""),
            ("user", "用户最新输入：{query}")
        ])

    def process(self, query: str, history: str = "无历史对话", user_profile_tags: str = ""):
        logger.info(f"[IntentGateway] 意图分析: {query}")
        logger.info(f"[IntentGateway] 历史对话长度: {len(history) if history else 0}")

        chain = self.prompt | self.structured_llm
        try:
            result = chain.invoke({
                "query": query,
                "history": history[-1000:],  # 增加历史长度到1000字符
                "user_profile_tags": user_profile_tags
            })

            # 验证工具参数完整性
            if result.intent_type == "tool_only" and result.tool_name:
                result = self._validate_tool_args(result, query, history)

            return result
        except Exception as e:
            logger.error(f"[IntentGateway] 网关解析失败: {e}")
            return GatewayOutput(
                intent_type="planning",
                true_intent=query,
                rag_keyword=query,
                mcp_keyword=query
            )

    def _validate_tool_args(self, result: GatewayOutput, query: str, history: str) -> GatewayOutput:
        """验证并补全工具参数"""
        tool_name = result.tool_name
        tool_args = result.tool_args.copy()

        if tool_name == "weather_query_skill":
            if not tool_args.get("city"):
                city = self._extract_city_from_history(history, query)
                if city:
                    tool_args["city"] = city
                    logger.info(f"[IntentGateway] 从历史中补全城市参数: {city}")
                else:
                    logger.warning(f"[IntentGateway] 无法确定城市，转为规划类意图")
                    result.intent_type = "planning"
                    result.rag_keyword = query
                    result.mcp_keyword = query

        result.tool_args = tool_args
        return result

    def _extract_city_from_history(self, history: str, query: str) -> str:
        """从历史对话中提取城市信息"""
        import re

        cities = [
            "北京", "上海", "广州", "深圳", "成都", "重庆", "杭州", "武汉", "西安", "苏州",
            "南京", "天津", "郑州", "长沙", "青岛", "大连", "厦门", "昆明", "贵阳", "哈尔滨",
            "长春", "沈阳", "济南", "太原", "石家庄", "合肥", "福州", "南昌", "南宁", "兰州",
            "银川", "西宁", "拉萨", "乌鲁木齐", "呼和浩特", "海口", "三亚", "珠海", "汕头",
            "桂林", "丽江", "大理", "西双版纳", "九寨沟", "黄山", "张家界", "泰山", "华山"
        ]

        # 先从当前query中找
        for city in cities:
            if city in query:
                return city

        # 再从历史中找（优先最近的对话）
        if history:
            lines = history.strip().split('\n')
            for line in reversed(lines):
                for city in cities:
                    if city in line:
                        return city

        return ""
