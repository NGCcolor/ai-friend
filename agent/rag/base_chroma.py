# agent/rag/base_chroma.py

from langchain_community.vectorstores import Chroma
from model.factory import embed_model  # 【完美对齐】：导入你工厂里的 embed_model
from utils.config_handler import chroma_conf  # 【完美对齐】：导入你配置类的 chroma_conf

# 读取配置文件中的全局存储路径
PERSIST_DIR = chroma_conf.get("persist_directory", "chroma_db")


class BaseChromaDB:
    def __init__(self, collection_name: str):
        """
        初始化 Chroma 向量库基类
        :param collection_name: 集合(表)的名称
        """
        self.collection_name = collection_name

        # 实例化具体的 Collection，注入通义千问的 embedding
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=embed_model,
            persist_directory=PERSIST_DIR
        )

    def persist(self):
        """持久化到磁盘"""
        self.vector_store.persist()