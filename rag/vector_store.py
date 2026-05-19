from langchain_chroma import Chroma
from langchain_core.documents import Document
from config import settings
from model.factory import embed_model
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.path_tool import get_abs_path
from utils.file_handler import pdf_loader, txt_loader, listdir_with_allowed_type, get_file_md5_hex
from utils.logger_handler import logger
import os


class VectorStoreService:
    """向量库服务类"""

    def __init__(self, collection_name: str = None):
        actual_collection_name = collection_name or settings.chroma.public_collection

        self.vector_store = Chroma(
            collection_name=actual_collection_name,
            embedding_function=embed_model,
            persist_directory=settings.chroma.persist_directory,
        )

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chroma.chunk_size,
            chunk_overlap=settings.chroma.chunk_overlap,
            separators=settings.chroma.separators,
            length_function=len,
        )

    def get_retriever(self, **kwargs):
        default_search_kwargs = {"k": settings.chroma.k}
        if "search_kwargs" in kwargs:
            custom_kwargs = kwargs.pop("search_kwargs")
            default_search_kwargs.update(custom_kwargs)
        return self.vector_store.as_retriever(search_kwargs=default_search_kwargs, **kwargs)

    def upsert_text(self, doc_id: str, text: str, metadata: dict):
        try:
            doc = Document(page_content=text, metadata=metadata)
            self.vector_store.add_documents([doc], ids=[doc_id])
            logger.info(f"[向量库] 成功更新 ID={doc_id} 的文本向量。")
            return True
        except Exception as e:
            logger.error(f"[向量库] 更新文本向量失败: {str(e)}")
            return False

    def similarity_search(self, query: str, k: int = 2) -> list[Document]:
        try:
            return self.vector_store.similarity_search(query, k=k)
        except Exception as e:
            logger.error(f"[向量库] 相似度检索失败: {str(e)}")
            return []

    def load_document(self):
        def check_md5_hex(md5_for_check: str):
            md5_file_path = get_abs_path(settings.chroma.md5_hex_store)
            if not os.path.exists(md5_file_path):
                open(md5_file_path, "w", encoding="utf-8").close()
                return False
            with open(md5_file_path, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    if line.strip() == md5_for_check:
                        return True
            return False

        def save_md5_hex(md5_for_check: str):
            md5_file_path = get_abs_path(settings.chroma.md5_hex_store)
            with open(md5_file_path, "a", encoding="utf-8") as f:
                f.write(md5_for_check + "\n")

        def get_file_documents(read_path: str):
            if read_path.endswith("txt"):
                return txt_loader(read_path)
            if read_path.endswith("pdf"):
                return pdf_loader(read_path)
            return []

        allowed_files_path = listdir_with_allowed_type(
            get_abs_path(settings.chroma.data_path),
            tuple(settings.chroma.allow_knowledge_file_type),
        )

        for path in allowed_files_path:
            md5_hex = get_file_md5_hex(path)
            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{path}内容已经存在知识库内，跳过")
                continue
            try:
                documents = get_file_documents(path)
                if not documents:
                    logger.warning(f"[加载知识库]{path}内没有有效文本内容，跳过")
                    continue
                split_document = self.spliter.split_documents(documents)
                if not split_document:
                    logger.warning(f"[加载知识库]{path}分片后没有有效文本内容，跳过")
                    continue
                self.vector_store.add_documents(split_document)
                save_md5_hex(md5_hex)
                logger.info(f"[加载知识库]{path} 内容加载成功")
            except Exception as e:
                logger.error(f"[加载知识库]{path}加载失败：{str(e)}", exc_info=True)


if __name__ == '__main__':
    vs = VectorStoreService()
    vs.load_document()
    retriever = vs.get_retriever()
    res = retriever.invoke("迷路")
    for r in res:
        print(r.page_content)
        print("-" * 20)