import requests
import random
from typing import Type
from pydantic import BaseModel
from langchain_core.tools import BaseTool

from config import settings
from utils.logger_handler import logger


class LocationPerceptionInput(BaseModel):
    pass


class LocationPerceptionSkill(BaseTool):
    name: str = "location_perception_skill"
    description: str = "【用户感知技能】获取用户当前真实所在的省份和城市。当需要为用户推荐附近的旅游景点，或需要确认用户的出发地时调用此技能。"
    args_schema: Type[BaseModel] = LocationPerceptionInput

    def _run(self) -> str:
        amap_key = settings.agent.amap_key
        if not amap_key:
            return "黑龙江省哈尔滨市中央大街"

        try:
            ip_url = f"https://restapi.amap.com/v3/ip?key={amap_key}"
            ip_res = requests.get(ip_url, timeout=5).json()

            rect = ip_res.get("rectangle")
            if not rect:
                return "哈尔滨市南岗区"

            p1, p2 = rect.split(";")
            lng1, lat1 = map(float, p1.split(","))
            lng2, lat2 = map(float, p2.split(","))
            center_lng, center_lat = (lng1 + lng2) / 2, (lat1 + lat2) / 2

            regeo_url = f"https://restapi.amap.com/v3/geocode/regeo?key={amap_key}&location={center_lng:.6f},{center_lat:.6f}&extensions=base"
            regeo_res = requests.get(regeo_url, timeout=5).json()

            if regeo_res.get("status") == "1":
                detail = regeo_res["regeocode"]["formatted_address"]
                logger.info(f"[{self.name}] 深度定位成功：{detail}")
                return detail

            return ip_res.get("city", "哈尔滨市")

        except Exception as e:
            logger.error(f"[{self.name}] 定位失败：{str(e)}")
            return "哈尔滨市中央大街"

