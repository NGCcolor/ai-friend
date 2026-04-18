from typing import List
from langchain_core.tools import BaseTool
from utils.logger_handler import logger
'''
这个类的作用是集中管理所有技能的注册和分发，避免在 Agent 初始化代码中硬编码一大堆 import。
'''
class SkillManager:
    """
    技能注册与管理器 (Registry Pattern)
    负责统一加载、管理和分发所有 Agent 技能
    """
    def __init__(self):
        self._skills: List[BaseTool] = []

    def register_skill(self, skill: BaseTool):
        """注册单个技能"""
        self._skills.append(skill)
        logger.debug(f"[SkillManager] 成功注册技能: {skill.name}")

    def register_skills(self, skills: List[BaseTool]):
        """批量注册技能"""
        for skill in skills:
            self.register_skill(skill)

    def get_all_skills(self) -> List[BaseTool]:
        """获取所有已注册的技能，供 LangChain bind_tools 使用"""
        return self._skills

# 全局单例管理器
skill_manager = SkillManager()