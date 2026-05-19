"""
统一配置管理模块
将所有配置集中到 settings.yaml 文件，提供全局配置实例
"""

import yaml
from pathlib import Path
from typing import Any, Dict


class Settings:
    """统一配置类，支持点号访问"""

    def __init__(self, config_path: str = "settings.yaml"):
        self._config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载 YAML 配置文件"""
        path = Path(__file__).parent / config_path
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.load(f, Loader=yaml.FullLoader)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value

    def __getattr__(self, name: str) -> Any:
        """支持点号访问"""
        if name.startswith("_"):
            return super().__getattribute__(name)
        value = self._config.get(name)
        if value is None:
            raise AttributeError(f"配置项 '{name}' 不存在")
        if isinstance(value, dict):
            return ConfigSection(value)
        return value

    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.get(key)

    def __repr__(self) -> str:
        return f"Settings({self._config})"


class ConfigSection:
    """配置节，支持点号访问嵌套配置"""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return super().__getattribute__(name)
        value = self._data.get(name)
        if value is None:
            raise AttributeError(f"配置项 '{name}' 不存在")
        if isinstance(value, dict):
            return ConfigSection(value)
        return value

    def __getitem__(self, key: str) -> Any:
        return self._data.get(key)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __repr__(self) -> str:
        return f"ConfigSection({self._data})"


# 全局配置实例
settings = Settings()


# 便捷访问函数
def get_model_config() -> ConfigSection:
    """获取模型配置"""
    return settings.model


def get_agent_config() -> ConfigSection:
    """获取 Agent 配置"""
    return settings.agent


def get_chroma_config() -> ConfigSection:
    """获取 Chroma 配置"""
    return settings.chroma


def get_prompts_config() -> ConfigSection:
    """获取提示词配置"""
    return settings.prompts


if __name__ == "__main__":
    # 测试配置加载
    print("=== 模型配置 ===")
    print(f"聊天模型: {settings.model.chat_model_name}")
    print(f"嵌入模型: {settings.model.embedding_model_name}")

    print("\n=== Agent 配置 ===")
    print(f"高德 Key: {settings.agent.amap_key}")

    print("\n=== Chroma 配置 ===")
    print(f"公共集合: {settings.chroma.public_collection}")
    print(f"持久化目录: {settings.chroma.persist_directory}")

    print("\n=== 提示词配置 ===")
    print(f"主提示词: {settings.prompts.main_prompt_path}")
