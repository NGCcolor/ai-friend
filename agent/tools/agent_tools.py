"""

D:\anac\envs\agent\python.exe -m streamlit run app.py

"""


import os
import requests
import datetime
from langchain_core.tools import tool
from rag.rag_service import RagSummarizeService
import random
from utils.config_handler import agent_conf
from utils.logger_handler import logger
rag = RagSummarizeService()
from utils.path_tool import get_abs_path
# 模拟用户ID池：用于随机返回用户ID
user_ids = ["1001", "1002", "1003", "1004", "1005", "1006", "1007", "1008", "1009", "1010"]
# 定义月份数组：存储2025年全年的年月字符串，格式为"YYYY-MM"
month_arr = [
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12"
]


# -------------------------- 配置区（替换为你的API密钥） --------------------------
# 1. 修复：API Key不需要get_abs_path（路径工具是给文件用的，Key是字符串）
HEWEATHER_KEY = agent_conf.get("HEWEATHER_KEY", "")  # 和风天气API Key
AMAP_KEY = agent_conf.get("AMAP_KEY", "").strip()        # 修复：高德Key不再错用和风Key

# 定义外部数据字典：key为月份字符串，value为对应的数据容器
# 用途：用于存储每个月份的外部业务数据（如每月的用户反馈、订单数据、统计结果等）
external_data = {}
# -------------------------- 工具定义 --------------------------
@tool(description="从向量存储中检索参考资料，回答用户关于扫地机器人的问题")
def rag_summarize(query: str) -> str:
    """
    RAG工具：调用向量库检索相似知识库内容，生成精准回答
    :param query: 用户的问题（如"扫地机器人迷路了怎么办"）
    :return: 基于知识库生成的总结回答
    """
    return rag.rag_summarize(query)


@tool(description="获取指定城市的天气信息，返回格式化天气描述")
def get_weather(city: str) -> str:
    """
    天气工具：基于高德地图API实现（仅依赖AMAP_KEY），兼容原有返回格式
    """
    if not city or city.strip() == "":
        return "城市名称不能为空，请输入有效城市名"

    # 校验高德Key配置
    if not AMAP_KEY:
        logger.error("❌ 错误：AMAP_KEY 未配置！")
        return "❌ 天气服务错误：高德API Key 未配置"

    try:
        # 步骤1：调用高德天气API（直接传城市名，无需先查城市ID）
        weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {
            "city": city.strip(),       # 城市名（支持中文，无需URL编码）
            "key": AMAP_KEY,            # 复用高德定位的Key
            "extensions": "base",       # base=实况天气，all=包含预报（按需切换）
            "output": "json",           # 返回JSON格式
            "language": "zh-CN"         # 中文返回
        }
        logger.info(f"🔍 查询高德天气接口：{weather_url}，参数：{params}")

        # 发送请求并处理响应
        res = requests.get(weather_url, params=params, timeout=10)
        res.raise_for_status()  # 触发HTTP错误（如403/404）
        weather_data = res.json()

        # 校验接口返回状态
        if weather_data.get("status") != "1":
            err_info = weather_data.get("info", "未知错误")
            err_code = weather_data.get("infocode", "无错误码")
            logger.error(f"❌ 高德天气查询失败：{err_info}（错误码：{err_code}）")
            return f"未查询到城市 {city} 的天气信息（错误：{err_info}）"

        # 提取实况天气数据（第一个结果即为目标城市）
        live_weather = weather_data.get("lives", [])
        if not live_weather:
            logger.error(f"❌ 未获取到 {city} 的实况天气数据")
            return f"未查询到城市 {city} 的实时天气信息"

        live = live_weather[0]
        # 🌟 修复核心：对可选字段做容错处理（用get方法，无值时显示"未知"）
        pressure = live.get("pressure", "未知")  # 气压字段容错
        temperature = live.get("temperature", "未知")
        humidity = live.get("humidity", "未知")
        winddirection = live.get("winddirection", "未知")
        windpower = live.get("windpower", "未知")
        reporttime = live.get("reporttime", "未知")
        weather = live.get("weather", "未知")

        # 格式化返回结果（对齐原有天气工具的输出格式，容错后不会报错）
        return (
            f"城市{city}实时天气：{weather}，气温{temperature}℃，"
            f"湿度{humidity}%，{winddirection}{windpower}级，"
            f"气压{pressure}hPa，发布时间：{reporttime}"
        )

    except requests.exceptions.Timeout:
        logger.error(f"❌ 查询{city}天气超时")
        return f"查询{city}天气超时，服务暂不可用"
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ 高德天气接口HTTP错误：{str(e)}")
        return f"天气服务接口错误：{str(e)[:30]}..."
    except Exception as e:
        logger.error(f"❌ 高德天气工具异常：{str(e)}", exc_info=True)
        return f"天气服务异常：{str(e)[:30]}..."

@tool(description="获取用户当前所在城市名称，用于定位服务")
def get_user_location() -> str:
    """
    定位工具：调用高德IP定位API获取真实城市，失败时返回随机城市
    :return: 真实/模拟城市名称
    """
    if not AMAP_KEY:
        logger.warning("高德API Key未配置，使用随机城市")
        return random.choice(["深圳", "合肥", "杭州"])

    try:
        ip_loc_url = f"https://restapi.amap.com/v3/ip?key={AMAP_KEY}"
        res = requests.get(ip_loc_url, timeout=10)
        res.raise_for_status()
        loc_data = res.json()

        if loc_data.get("status") == "1" and loc_data.get("city"):
            city = loc_data["city"].replace("市", "")
            logger.info(f"高德定位成功：{city}")
            return city
        else:
            logger.warning(f"高德定位无结果：{loc_data.get('info', '未知错误')}")
            return random.choice(["深圳", "合肥", "杭州"])
    except requests.exceptions.Timeout:
        logger.warning("高德定位超时，使用随机城市")
        return random.choice(["深圳", "合肥", "杭州"])
    except Exception as e:
        logger.error(f"高德定位异常：{str(e)}")
        return random.choice(["深圳", "合肥", "杭州"])


@tool(description="获取当前用户的唯一ID，用于身份识别")
def get_user_id() -> str:
    """
    用户ID工具：模拟获取用户ID（实际可从会话/用户系统中读取）
    :return: 随机返回一个用户ID字符串
    """
    return random.choice(user_ids)

@tool(description="获取当前的完整日期，返回格式为YYYY-MM-DD的字符串，用于日期相关查询")
def get_current_date() -> str:
    """
    日期工具：获取系统当前的完整日期（年-月-日）
    :return: 标准化的日期字符串，异常时返回默认日期
    """
    try:
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        logger.info(f"成功获取当前日期：{current_date}")
        return current_date
    except Exception as e:
        logger.error(f"获取当前日期异常：{str(e)}")
        return "2025-01-01"

def generate_external_data():
    """
    核心辅助函数：加载外部CSV数据文件，构建「用户ID→月份→使用记录」的多层字典
    数据结构设计：
    {
        "user_id": {          # 第一层：用户唯一标识
            "month" : {       # 第二层：月份（YYYY-MM）
                "特征": xxx,  # 第三层：用户该月使用特征
                "效率": xxx,  # 用户该月使用效率
                "耗材": xxx,  # 用户该月耗材使用情况
                "对比": xxx   # 用户该月数据与往期对比
            },
            ...
        },
        ...
    }
    :return: None（数据直接填充到全局external_data字典）
    """
    # 1. 仅在external_data为空时加载（避免重复读取文件，提升性能）
    if not external_data:
        # 2. 从Agent配置中获取外部数据文件的绝对路径
        external_data_path = get_abs_path(agent_conf["external_data_path"])

        # 3. 校验文件是否存在，不存在则抛出明确异常
        if not os.path.exists(external_data_path):
            raise FileNotFoundError(f"外部数据文件{external_data_path}不存在")

        # 4. 读取CSV文件并解析数据
        with open(external_data_path, "r", encoding="utf-8") as f:
            # 跳过首行（表头），遍历后续数据行
            for line in f.readlines()[1:]:
                # 按逗号分割每行数据，得到字段数组
                arr: list[str] = line.strip().split(",")

                # 5. 提取并清洗字段（去除可能的双引号，避免数据污染）
                user_id: str = arr[0].replace('"', "")    # 第1列：用户ID
                feature: str = arr[1].replace('"', "")    # 第2列：使用特征
                efficiency: str = arr[2].replace('"', "") # 第3列：使用效率
                consumables: str = arr[3].replace('"', "")# 第4列：耗材使用
                comparison: str = arr[4].replace('"', "") # 第5列：数据对比
                time: str = arr[5].replace('"', "")       # 第6列：月份（YYYY-MM）

                # 6. 构建多层字典：用户ID不存在则初始化空字典
                if user_id not in external_data:
                    external_data[user_id] = {}

                # 7. 填充当前用户-月份的使用记录
                external_data[user_id][time] = {
                    "特征": feature,
                    "效率": efficiency,
                    "耗材": consumables,
                    "对比": comparison,
                }

@tool(description="从外部系统中获取指定用户在指定月份的使用记录，以纯字符串形式返回， 如果未检索到返回空字符串")
def fetch_external_data(user_id: str, month: str) -> str:
    """
    外部数据查询工具：根据用户ID+月份，检索对应的使用记录
    :param user_id: 用户唯一标识（如"1003"）
    :param month: 月份字符串（如"2025-05"）
    :return: 匹配到的使用记录字典（转字符串），未匹配则返回空字符串
    """
    # 1. 确保外部数据已加载（首次调用时自动加载）
    generate_external_data()

    try:
        # 2. 检索指定用户+月份的记录，返回字符串格式（适配大模型输入）
        return str(external_data[user_id][month])
    except KeyError:
        # 3. 检索失败时记录日志，返回空字符串（避免Agent报错）
        logger.warning(f"[fetch_external_data]未能检索到用户：{user_id}在{month}的使用记录数据")
        return ""

@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    """
    上下文填充工具：为报告生成场景注入动态上下文（核心是触发中间件逻辑）
    注：该工具本身仅返回标识字符串，实际上下文注入逻辑在中间件中实现
    :return: 固定字符串，标识工具已调用（如"fill_context_for_report已调用"）
    """
    return "fill_context_for_report已调用"

@tool(description="获取当前的完整日期，返回格式为YYYY-MM-DD的字符串，用于日期相关查询")
def get_current_date() -> str:
    """
    日期工具：获取系统当前的完整日期（年-月-日），保证格式统一且无异常
    :return: 标准化的日期字符串（如"2026-03-16"），异常时返回默认日期提示
    """
    try:
        # 获取当前本地时间并格式化为YYYY-MM-DD，适配所有系统环境
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        logger.info(f"成功获取当前日期：{current_date}")
        return current_date
    except Exception as e:
        # 极端异常场景降级，返回默认日期并记录日志
        logger.error(f"获取当前日期异常：{str(e)}")
        return "2025-01-01"  # 默认兜底日期


if __name__ == '__main__':
    # 单独测试每个工具（验证解耦性）
    print("=== 测试定位工具 ===")
    print(get_weather())

