import datetime
from typing import Type
from pydantic import BaseModel
from langchain_core.tools import BaseTool
from utils.logger_handler import logger


class TimePerceptionInput(BaseModel):
    pass


class TimePerceptionSkill(BaseTool):
    name: str = "time_perception_skill"
    description: str = "【环境感知技能】获取当前的精确时间、日期、星期几和季节。在安排旅游路线时必须优先调用此技能。"
    args_schema: Type[BaseModel] = TimePerceptionInput

    def _run(self) -> str:
        try:
            now = datetime.datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M:%S")

            month = now.month
            season = "春季" if month in (3, 4, 5) else "夏季" if month in (6, 7, 8) else "秋季" if month in (
            9, 10, 11) else "冬季"
            weekday_map = {0: "星期一", 1: "星期二", 2: "星期三", 3: "星期四", 4: "星期五", 5: "星期六", 6: "星期日"}
            weekday = weekday_map[now.weekday()]

            result = f"当前日期：{current_date}，时间：{current_time}，{weekday}，当前季节：{season}。"
            return result
        except Exception as e:
            logger.error(f"[{self.name}] 异常：{str(e)}")
            return "获取时间失败"