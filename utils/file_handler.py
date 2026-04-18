""""
文件加载工具
"""
import os
import hashlib

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from utils.logger_handler import logger

def get_file_md5_hex(filepath: str):
    """获取文件的MD5十六进制字符串"""
    if not os.path.exists(filepath):
        logger.error(f"[md5计算]文件{filepath}不存在")
        return
    if not os.path.isfile(filepath):
        logger.error(f"[md5计算]路径{filepath}不是文件")
        return

    md5_obj = hashlib.md5()
    chunk_size = 4096  # 4KB分片，避免大文件占内存

    try:
        with open(filepath, "rb") as f:  # 必须二进制读取
            while chunk := f.read(chunk_size):
                md5_obj.update(chunk)
        md5_hex = md5_obj.hexdigest()
        return md5_hex
    except Exception as e:
        logger.error(f"计算文件{filepath}md5失败: {str(e)}")
        return None


""""
精准筛选指定文件夹下，后缀符合要求的所有文件，并返回这些文件的完整路径
（仅遍历当前文件夹，不深入子文件夹），是文件批量处理场景中非常实用的工具函数。
"""
def listdir_with_allowed_type(path: str, allowed_types: tuple[str]):
    """返回文件夹内指定后缀的文件路径列表（仅当前目录，不递归子目录）"""
    files = []

    # 校验路径是否为文件夹
    if not os.path.isdir(path):
        logger.error(f"[listdir_with_allowed_type]{path}不是文件夹")
        return tuple()  # 修正：返回空元组更合理，避免返回类型不匹配

    # 遍历目录下所有条目
    for f in os.listdir(path):
        # 筛选后缀匹配的文件
        if f.endswith(allowed_types):
            # 拼接完整路径并加入列表
            files.append(os.path.join(path, f))

    # 返回不可变元组（避免外部修改）
    return tuple(files)

def pdf_loader(filepath: str, passwd=None) -> list[Document]:
    """
    加载PDF文件，返回Langchain Document列表
    :param filepath: PDF文件路径
    :param passwd: 加密PDF的密码（可选）
    :return: 包含页面内容和元数据的Document对象列表
    """
    return PyPDFLoader(filepath, password=passwd).load()

def txt_loader(filepath: str) -> list[Document]:
    """
    加载TXT文本文件，返回Langchain Document列表
    :param filepath: TXT文件路径
    :return: 包含文本内容和元数据的Document对象列表
    """
    return TextLoader(filepath, encoding="utf-8").load()