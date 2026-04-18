import json
from typing import List
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from rag.vector_store import VectorStoreService
from utils.prompt_loader import load_rag_prompts
from model.factory import chat_model
from utils.logger_handler import logger
from utils.config_handler import chroma_conf  # 【新增】：引入配置管理器

class RagSummarizeService(object):
    """
    RAG 总结服务类（单体 Agent 纯向量架构版）
    核心能力：
    1. HyDE 机制：将短 Query 升维为长段假设性文档（对应简历：检索引擎 HyDE 升维）
    2. 阈值熔断：相似度 < 0.8 直接丢弃（对应简历：设置相似度阈值，小于0.8直接放弃）
    """
    def __init__(self):
        self.model = chat_model

        # =======================================================
        # 【核心修改】：明确绑定公共知识库！
        # 读取 yaml 中配置的公共表名，如果没有则默认使用 "public_knowledge"
        # =======================================================
        public_collection = chroma_conf.get("public_collection", "public_knowledge")
        self.vector_store = VectorStoreService(collection_name=public_collection)

        # 2. 获取带有“严格阈值过滤”的检索器 (对应简历：小于0.8直接放弃参考)
        # LangChain 原生支持 similarity_score_threshold 类型的检索
        self.retriever = self.vector_store.get_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "score_threshold": 0.8,  # 低于 0.8 相似度的文档将被自动剔除
                "k": 3                   # 最多返回 3 篇高质量文档
            }
        )

        # 3. 初始化 RAG 总结生成链
        self.prompt_template = PromptTemplate.from_template(load_rag_prompts())
        self.chain = self.prompt_template | self.model | StrOutputParser()

    def _generate_hyde_document(self, query: str) -> str:
        """
        核心亮点：生成假设性文档 (HyDE)
        （告别“假答案”这种口语，代码里我们叫 Hypothetical Document）
        """
        logger.info(f"[RAG-HyDE] 正在为 Query 升维生成假设性文档: {query}")

        hyde_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个旅游领域的知识检索增强节点。
请根据用户的提问，直接编写一段假想的、详细的回答。
注意：不需要考虑事实是否绝对准确，目的是尽可能多地在回答中包含相关的地名、特色、专有名词、形容词，以此扩充语义特征向量空间。"""),
            ("user", "{query}")
        ])

        try:
            # 调用大模型生成这段富含关键词的假想文章
            hypothetical_doc = (hyde_prompt | self.model).invoke({"query": query}).content
            logger.debug(f"[RAG-HyDE] 升维结果: {hypothetical_doc}")
            return hypothetical_doc
        except Exception as e:
            logger.error(f"[RAG-HyDE] 假设文档生成失败，降级使用原 Query: {e}")
            return query

    def retriever_docs(self, query: str, use_hyde: bool = True) -> List[Document]:
        """
        执行向量检索
        """
        # 如果开启了 HyDE，则使用生成出来的长文章去搜库；否则用短句原话搜库
        search_query = self._generate_hyde_document(query) if use_hyde else query

        logger.info("[RAG] 开始执行纯向量相似度检索 (阈值=0.8)...")
        # 这里的 retriever 已经在 __init__ 里配置了 0.8 的拦截机制
        docs = self.retriever.invoke(search_query)

        if not docs:
            logger.warning("[RAG] 触发熔断：未匹配到相似度 >= 0.8 的高质量文档。")

        return docs

    def rag_summarize(self, query: str) -> str:
        """
        顶层核心接口：供 Agent 的 Skill 或 Tool 调用
        """
        # 1. 通过 HyDE 和 阈值熔断 获取高质量资料
        context_docs = self.retriever_docs(query, use_hyde=True)

        # 如果被 0.8 的阈值全挡住了，直接告诉主 Agent 没找到，防幻觉
        if not context_docs:
            return "知识库中未检索到置信度达标（相似度 >= 0.8）的参考资料，请直接告知用户暂无内部收录信息。"

        # 2. 组装上下文
        context = ""
        for i, doc in enumerate(context_docs, 1):
            # 将 md5 或来源文件等 metadata 一并喂给大模型
            context += f"【参考资料 {i}】\n内容：{doc.page_content}\n"
            if doc.metadata:
                context += f"元数据：{doc.metadata}\n"
            context += "-" * 30 + "\n"

        logger.info("[RAG] RAG 上下文拼装完成，交由大模型归纳。")

        # 3. 将用户问题和拼好的高质量 context 丢给大模型做最终总结
        return self.chain.invoke({
            "input": query,
            "context": context
        })

if __name__ == '__main__':
    rag = RagSummarizeService()
    # 测试一下效果
    print(rag.rag_summarize("帮我看看哈尔滨中央大街有啥好吃的？"))