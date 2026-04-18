import requests
import random
from typing import Type
from pydantic import BaseModel
from langchain_core.tools import BaseTool

from utils.config_handler import agent_conf
from utils.logger_handler import logger


# 定义输入Schema（无参数也需要定义空Schema以保证规范）
class LocationPerceptionInput(BaseModel):
    pass


class LocationPerceptionSkill(BaseTool):
    name: str = "location_perception_skill"
    description: str = "【用户感知技能】获取用户当前真实所在的省份和城市。当需要为用户推荐附近的旅游景点，或需要确认用户的出发地时调用此技能。"
    args_schema: Type[BaseModel] = LocationPerceptionInput

    def _run(self) -> str:
        amap_key = agent_conf.get("AMAP_KEY", "").strip()
        if not amap_key:
            return "黑龙江省哈尔滨市中央大街"  # 默认兜底

        try:
            # 1. 第一步：获取当前 IP 的经纬度中心点
            ip_url = f"https://restapi.amap.com/v3/ip?key={amap_key}"
            ip_res = requests.get(ip_url, timeout=5).json()

            # 提取矩形范围的中心点 (高德 IP 接口返回 rectangle: x1,y1;x2,y2)
            rect = ip_res.get("rectangle")
            if not rect:
                return "哈尔滨市南岗区"

                # 取矩形对角线的中心点作为估算坐标
            p1, p2 = rect.split(";")
            lng1, lat1 = map(float, p1.split(","))
            lng2, lat2 = map(float, p2.split(","))
            center_lng, center_lat = (lng1 + lng2) / 2, (lat1 + lat2) / 2

            # 2. 第二步：调用逆地理编码接口 (ReGeo) 获取详细街道
            regeo_url = f"https://restapi.amap.com/v3/geocode/regeo?key={amap_key}&location={center_lng:.6,f},{center_lat:.6,f}&extensions=base"
            regeo_res = requests.get(regeo_url, timeout=5).json()

            if regeo_res.get("status") == "1":
                address_component = regeo_res["regeocode"]["addressComponent"]
                # 提取：省 + 市 + 区 + 街道 + 门牌号
                detail = regeo_res["regeocode"]["formatted_address"]

                logger.info(f"[{self.name}] 深度定位成功：{detail}")
                return detail

            return ip_res.get("city", "哈尔滨市")

        except Exception as e:
            logger.error(f"[{self.name}] 定位失败：{str(e)}")
            return "哈尔滨市中央大街"

