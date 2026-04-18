import requests
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from utils.config_handler import agent_conf
from utils.logger_handler import logger


class RoutePlanningInput(BaseModel):
    origin: str = Field(..., description="出发地的经纬度，格式为'经度,纬度'，例如'116.481028,39.989643'")
    destination: str = Field(..., description="目的地的经纬度，格式为'经度,纬度'")
    city: str = Field(..., description="所在城市名称，如'哈尔滨'")


class TransitRouteSkill(BaseTool):
    name: str = "transit_route_skill"
    description: str = "【导航规划技能】获取两个地点之间的详细公共交通（公交/地铁）换乘路线。当用户选定具体景点，需要生成保姆级交通指南时必须调用此技能。"
    args_schema: Type[BaseModel] = RoutePlanningInput

    def _run(self, origin: str, destination: str, city: str) -> str:
        amap_key = agent_conf.get("AMAP_KEY", "").strip()
        if not amap_key:
            return "导航服务错误：未配置高德API Key"

        try:
            # 调用高德公交路径规划 API (v3)
            url = "https://restapi.amap.com/v3/direction/transit/integrated"
            params = {
                "key": amap_key,
                "origin": origin,
                "destination": destination,
                "city": city,
                "extensions": "all",  # 返回详细信息
                "output": "json"
            }

            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
            route_data = res.json()

            if route_data.get("status") != "1" or not route_data.get("route", {}).get("transits"):
                return f"未查询到从 {origin} 到 {destination} 的有效公交路线。"

            # 提取第一条最推荐的路线
            best_transit = route_data["route"]["transits"][0]
            distance = int(best_transit.get("distance", 0)) / 1000  # 转公里
            duration = int(best_transit.get("duration", 0)) / 60  # 转分钟

            segments_desc = []
            for segment in best_transit.get("segments", []):
                bus = segment.get("bus", {}).get("buslines", [])
                if bus:
                    bus_info = bus[0]
                    name = bus_info.get("name", "").split("(")[0]  # 清洗冗余信息
                    start_stop = bus_info.get("departure_stop", {}).get("name", "")
                    end_stop = bus_info.get("arrival_stop", {}).get("name", "")
                    via_num = bus_info.get("via_num", "几")
                    segments_desc.append(f"在【{start_stop}】乘坐 {name}，经过 {via_num} 站，在【{end_stop}】下车")

            # 拼接保姆级导航文案
            nav_text = f"总路程约{distance:.1f}公里，预计耗时{duration:.0f}分钟。\n交通指南：" + " -> ".join(segments_desc)
            return nav_text

        except Exception as e:
            logger.error(f"[{self.name}] 导航规划异常：{str(e)}")
            return "导航服务暂不可用，建议打车前往。"