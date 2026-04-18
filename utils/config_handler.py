# 导入YAML处理模块，用于解析.yml配置文件
import yaml
# 导入自定义路径工具函数，获取项目绝对路径
from utils.path_tool import get_abs_path


def load_rag_config(config_path: str = get_abs_path("config/rag.yml"), encoding: str = "utf-8") -> dict:
    """
    加载RAG(检索增强生成)模块配置

    :param config_path: 配置文件路径，默认指向项目根目录下 config/rag.yml
    :param encoding: 文件编码格式，默认UTF-8防止中文乱码
    :return: 解析后的配置字典 dict
    """
    with open(config_path, "r", encoding=encoding) as f:
        # 使用FullLoader加载，避免安全警告，解析YAML内容为Python字典
        return yaml.load(f, Loader=yaml.FullLoader)


def load_chroma_config(config_path: str = get_abs_path("config/chroma.yml"), encoding: str = "utf-8") -> dict:
    """
    加载Chroma向量数据库配置

    :param config_path: 配置文件路径，默认指向项目根目录下 config/chroma.yml
    :param encoding: 文件编码格式
    :return: 解析后的配置字典 dict
    """
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def load_prompts_config(config_path: str = get_abs_path("config/prompts.yml"), encoding: str = "utf-8") -> dict:
    """
    加载Agent提示词(Prompt)配置

    :param config_path: 配置文件路径，默认指向项目根目录下 config/prompts.yml
    :param encoding: 文件编码格式
    :return: 解析后的配置字典 dict
    """
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def load_agent_config(config_path: str = get_abs_path("config/agent.yml"), encoding: str = "utf-8") -> dict:
    """
    加载Agent核心框架配置

    :param config_path: 配置文件路径，默认指向项目根目录下 config/agent.yml
    :param encoding: 文件编码格式
    :return: 解析后的配置字典 dict
    """
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


# -------------------------- 全局配置实例化 --------------------------
# 加载RAG配置，全局可调用
rag_conf = load_rag_config()
# 加载Chroma向量库配置，全局可调用
chroma_conf = load_chroma_config()
# 加载提示词配置，全局可调用
prompts_conf = load_prompts_config()
# 加载Agent核心配置，全局可调用
agent_conf = load_agent_config()