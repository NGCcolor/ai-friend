# agent/rag/base_chroma.py

from langchain_community.vectorstores import Chroma
from model.factory import embed_model
from config import settings


class BaseChromaDB:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=embed_model,
            persist_directory=settings.chroma.persist_directory
        )

    def persist(self):
        self.vector_store.persist()