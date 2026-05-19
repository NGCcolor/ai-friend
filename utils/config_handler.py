"""
配置处理模块 - 兼容旧代码的快捷访问
统一使用 config.py 中的 settings 实例
"""

from config import settings

# 兼容旧代码的全局配置实例
rag_conf = {
    "chat_model_name": settings.model.chat_model_name,
    "embedding_model_name": settings.model.embedding_model_name,
}

chroma_conf = {
    "collection_name": settings.chroma.public_collection,
    "public_collection": settings.chroma.public_collection,
    "profile_collection_name": settings.chroma.profile_collection,
    "history_collection_name": settings.chroma.history_collection,
    "persist_directory": settings.chroma.persist_directory,
    "k": settings.chroma.k,
    "data_path": settings.chroma.data_path,
    "md5_hex_store": settings.chroma.md5_hex_store,
    "allow_knowledge_file_type": settings.chroma.allow_knowledge_file_type,
    "chunk_size": settings.chroma.chunk_size,
    "chunk_overlap": settings.chroma.chunk_overlap,
    "separators": settings.chroma.separators,
}

prompts_conf = {
    "main_prompt_path": settings.prompts.main_prompt_path,
    "rag_summarize_prompt_path": settings.prompts.rag_summarize_prompt_path,
    "report_prompt_path": settings.prompts.report_prompt_path,
}

agent_conf = {
    "external_data_path": settings.agent.external_data_path,
    "HEWEATHER_KEY": settings.agent.heweather_key,
    "AMAP_KEY": settings.agent.amap_key,
}
