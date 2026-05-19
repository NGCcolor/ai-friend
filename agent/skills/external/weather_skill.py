import requests
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from config import settings
from utils.logger_handler import logger


class WeatherQueryInput(BaseModel):
    city: str = Field(..., description="需要查询天气的目标城市名称，如'北京市'")


class WeatherQuerySkill(BaseTool):
    name: str = "weather_query_skill"
    description: str = "【外部交互技能】获取指定城市的天气信息。在规划出行路线或推荐景点前必须调用此技能确认天气条件。"
    args_schema: Type[BaseModel] = WeatherQueryInput

    def _run(self, city: str) -> str:
        amap_key = settings.agent.amap_key
        if not amap_key:
            return "天气服务错误：高德API Key 未配置"

        try:
            weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"
            params = {"city": city.strip(), "key": amap_key, "extensions": "base"}
            res = requests.get(weather_url, params=params, timeout=10)
            res.raise_for_status()
            weather_data = res.json()

            if weather_data.get("status") != "1" or not weather_data.get("lives"):
                return f"未查询到城市 {city} 的实时天气信息"

            live = weather_data["lives"][0]
            return (f"{city}实时天气：{live.get('weather')}，气温{live.get('temperature')}℃，"
                    f"风向{live.get('winddirection')}，风力{live.get('windpower')}级。")
        except Exception as e:
            logger.error(f"[{self.name}] 异常：{str(e)}")
            return f"天气服务异常：{str(e)[:30]}"


if __name__ == '__main__':
    weather_skill = WeatherQuerySkill()
    print("=== 测试天气技能 ===")
    test_city = "哈尔滨"
    print(f"正在查询【{test_city}】的天气...")
    result = weather_skill.invoke({"city": test_city})
    print("返回结果:", result)