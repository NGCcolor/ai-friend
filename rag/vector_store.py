from langchain_chroma import Chroma
from langchain_core.documents import Document
from utils.config_handler import chroma_conf
from model.factory import embed_model
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.path_tool import get_abs_path
from utils.file_handler import pdf_loader, txt_loader, listdir_with_allowed_type, get_file_md5_hex
from utils.logger_handler import logger
import os

"""
将数据进行转化为向量存储在向量库中
"""


class VectorStoreService:
    """
    向量库服务类：封装Chroma向量库的初始化、检索、文档加载入库核心逻辑
    核心能力：
    1. 初始化Chroma向量库和文本分割器
    2. 提供向量检索器（支持动态参数透传）
    3. 加载指定目录的TXT/PDF文件，MD5去重后切分入库
    """

    def __init__(self, collection_name: str = None):
        """初始化向量库和文本分割器（支持动态集合名称隔离不同业务）"""

        # 1. 动态获取集合名称：传了就用传的，没传就读配置里的默认值
        actual_collection_name = collection_name if collection_name else chroma_conf["collection_name"]

        # 2. 初始化Chroma向量库
        self.vector_store = Chroma(
            collection_name=actual_collection_name,  # 向量库集合名（隔离不同业务）
            embedding_function=embed_model,  # 嵌入模型（文本转向量）
            persist_directory=chroma_conf["persist_directory"],  # 向量数据持久化目录
        )

        # 3. 初始化文本分割器（解决长文本向量化问题）
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],  # 每个文本块最大字符数
            chunk_overlap=chroma_conf["chunk_overlap"],  # 相邻块重叠字符数（保证语义连贯）
            separators=chroma_conf["separators"],  # 文本分割优先级（先段落、再换行、再标点）
            length_function=len,  # 字符长度计算方式
        )

    def get_retriever(self, **kwargs):
        """
        获取向量检索器（用于RAG流程中检索相似文本）
        完美修复：通过 **kwargs 支持动态接收 search_type 和 search_kwargs
        """
        # 1. 读取配置文件中的默认参数
        default_search_kwargs = {"k": chroma_conf["k"]}

        # 2. 如果外部调用方（如 rag_service.py）传了自定义的 search_kwargs，将其与默认配置合并，外部优先级更高
        if "search_kwargs" in kwargs:
            custom_kwargs = kwargs.pop("search_kwargs")
            default_search_kwargs.update(custom_kwargs)

        # 3. 将合并后的 search_kwargs 和其他所有额外参数透传给底层的 as_retriever
        return self.vector_store.as_retriever(search_kwargs=default_search_kwargs, **kwargs)

    def upsert_text(self, doc_id: str, text: str, metadata: dict):
        """直接把纯文本存入向量库的方法（供保存画像Skill调用）"""
        try:
            doc = Document(page_content=text, metadata=metadata)
            self.vector_store.add_documents([doc], ids=[doc_id])
            logger.info(f"[向量库] 成功更新 ID={doc_id} 的文本向量。")
            return True
        except Exception as e:
            logger.error(f"[向量库] 更新文本向量失败: {str(e)}")
            return False

    def similarity_search(self, query: str, k: int = 2) -> list[Document]:
        """根据语义检索相似向量的方法（供检索画像Skill调用）"""
        try:
            return self.vector_store.similarity_search(query, k=k)
        except Exception as e:
            logger.error(f"[向量库] 相似度检索失败: {str(e)}")
            return []

    def load_document(self):
        """
        核心方法：从指定目录加载TXT/PDF文件，MD5去重后切分存入向量库
        """

        def check_md5_hex(md5_for_check: str):
            md5_file_path = get_abs_path(chroma_conf["md5_hex_store"])
            if not os.path.exists(md5_file_path):
                open(md5_file_path, "w", encoding="utf-8").close()
                return False

            with open(md5_file_path, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line == md5_for_check:
                        return True
                return False

        def save_md5_hex(md5_for_check: str):
            md5_file_path = get_abs_path(chroma_conf["md5_hex_store"])
            with open(md5_file_path, "a", encoding="utf-8") as f:
                f.write(md5_for_check + "\n")

        def get_file_documents(read_path: str):
            if read_path.endswith("txt"):
                return txt_loader(read_path)
            if read_path.endswith("pdf"):
                return pdf_loader(read_path)
            return []

        allowed_files_path: list[str] = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        for path in allowed_files_path:
            md5_hex = get_file_md5_hex(path)
            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{path}内容已经存在知识库内，跳过")
                continue

            try:
                documents: list[Document] = get_file_documents(path)
                if not documents:
                    logger.warning(f"[加载知识库]{path}内没有有效文本内容，跳过")
                    continue

                split_document: list[Document] = self.spliter.split_documents(documents)
                if not split_document:
                    logger.warning(f"[加载知识库]{path}分片后没有有效文本内容，跳过")
                    continue

                self.vector_store.add_documents(split_document)
                save_md5_hex(md5_hex)
                logger.info(f"[加载知识库]{path} 内容加载成功")

            except Exception as e:
                logger.error(f"[加载知识库]{path}加载失败：{str(e)}", exc_info=True)
                continue


if __name__ == '__main__':
    vs = VectorStoreService()
    vs.load_document()
    retriever = vs.get_retriever()
    res = retriever.invoke("迷路")
    for r in res:
        print(r.page_content)
        print("-" * 20)