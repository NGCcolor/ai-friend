import json
from typing import List
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from rag.vector_store import VectorStoreService
from utils.prompt_loader import load_rag_prompts
from model.factory import chat_model
from utils.logger_handler import logger
from config import settings


class RagSummarizeService(object):
    """RAG 总结服务类"""

    def __init__(self):
        self.model = chat_model
        public_collection = settings.chroma.public_collection
        self.vector_store = VectorStoreService(collection_name=public_collection)

        self.retriever = self.vector_store.get_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "score_threshold": 0.8,
                "k": 3
            }
        )

        self.prompt_template = PromptTemplate.from_template(load_rag_prompts())
        self.chain = self.prompt_template | self.model | StrOutputParser()

    def _generate_hyde_document(self, query: str) -> str:
        logger.info(f"[RAG-HyDE] 正在为 Query 升维生成假设性文档: {query}")
        hyde_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个旅游领域的知识检索增强节点。
请根据用户的提问，直接编写一段假想的、详细的回答。
注意：不需要考虑事实是否绝对准确，目的是尽可能多地在回答中包含相关的地名、特色、专有名词、形容词，以此扩充语义特征向量空间。"""),
            ("user", "{query}")
        ])
        try:
            hypothetical_doc = (hyde_prompt | self.model).invoke({"query": query}).content
            logger.debug(f"[RAG-HyDE] 升维结果: {hypothetical_doc}")
            return hypothetical_doc
        except Exception as e:
            logger.error(f"[RAG-HyDE] 假设文档生成失败，降级使用原 Query: {e}")
            return query

    def retriever_docs(self, query: str, use_hyde: bool = True) -> List[Document]:
        search_query = self._generate_hyde_document(query) if use_hyde else query
        logger.info("[RAG] 开始执行纯向量相似度检索 (阈值=0.8)...")
        docs = self.retriever.invoke(search_query)
        if not docs:
            logger.warning("[RAG] 触发熔断：未匹配到相似度 >= 0.8 的高质量文档。")
        return docs

    def rag_summarize(self, query: str) -> str:
        context_docs = self.retriever_docs(query, use_hyde=True)
        if not context_docs:
            return "知识库中未检索到置信度达标（相似度 >= 0.8）的参考资料，请直接告知用户暂无内部收录信息。"
        context = ""
        for i, doc in enumerate(context_docs, 1):
            context += f"【参考资料 {i}】\n内容：{doc.page_content}\n"
            if doc.metadata:
                context += f"元数据：{doc.metadata}\n"
            context += "-" * 30 + "\n"
        logger.info("[RAG] RAG 上下文拼装完成，交由大模型归纳。")
        return self.chain.invoke({"input": query, "context": context})


if __name__ == "__main__":
    rag = RagSummarizeService()
    print(rag.rag_summarize("帮我看看哈尔滨中央大街有啥好吃的？"))
