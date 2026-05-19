from abc import ABC, abstractmethod
from typing import Optional
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_openai import ChatOpenAI
from config import settings


class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        pass


class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return ChatOpenAI(
            model=settings.model.chat_model_name,
            api_key=settings.model.chat_api_key,
            base_url=settings.model.chat_base_url,
            temperature=0.7,
            extra_body={"enable_thinking": False},
        )


class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return DashScopeEmbeddings(
            model=settings.model.embedding_model_name,
            dashscope_api_key=settings.model.embedding_api_key
        )


chat_model = ChatModelFactory().generator()
embed_model = EmbeddingsFactory().generator()
