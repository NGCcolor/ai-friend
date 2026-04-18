from abc import ABC, abstractmethod  # 抽象基类与抽象方法装饰器
from typing import Optional  # 类型标注：可选类型
from langchain_core.embeddings import Embeddings  # LangChain 嵌入模型基类
from langchain_community.chat_models.tongyi import BaseChatModel  # 通义千问聊天模型基类
from langchain_community.embeddings import DashScopeEmbeddings  # 阿里云通义千问嵌入模型实现
from langchain_community.chat_models.tongyi import ChatTongyi  # 阿里云通义千问聊天模型实现
from utils.config_handler import rag_conf  # 加载 RAG 配置（含模型名称）

# 抽象工厂基类：定义模型生成接口
class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        """
        抽象方法：生成模型实例
        :return: 可返回 Embeddings 或 BaseChatModel 实例，或 None
        """
        pass

# 聊天模型工厂：负责生成通义千问聊天模型
class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        """
        生成通义千问聊天模型实例
        :return: ChatTongyi 实例，从配置读取模型名称
        """
        return ChatTongyi(
            model=rag_conf["chat_model_name"],
            dashscope_api_key="sk-5a198bfa388c46f68955df8dbbd9ce20"
        )

# 嵌入模型工厂：负责生成通义千问嵌入模型
class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        """
        生成通义千问嵌入模型实例
        :return: DashScopeEmbeddings 实例，从配置读取模型名称
        """
        return DashScopeEmbeddings(
            model=rag_conf["embedding_model_name"],
            dashscope_api_key="sk-5a198bfa388c46f68955df8dbbd9ce20"
        )

chat_model=ChatModelFactory().generator()
embed_model=EmbeddingsFactory().generator()


