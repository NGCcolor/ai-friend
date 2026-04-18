import requests
import json
import time  # 引入 time 模块用于休眠
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from utils.logger_handler import logger


# ==========================================
# 技能：通过封装的 HTTP MCP 协议搜索小红书笔记 + 获取详情正文
# ==========================================
class XhsSearchInput(BaseModel):
    keyword: str = Field(..., description="需要搜索的小红书关键词，如 '哈尔滨 中央大街 避雷' 或 '唐山 旅游攻略'")


class XhsMcpSearchSkill(BaseTool):
    name: str = "xhs_mcp_search_skill"
    description: str = "【实时攻略检索技能】通过小红书接口实时搜索真实用户游记。不仅获取标题，还会拉取前3篇高赞帖子的【正文详情】，用于精准判断评价是好是坏、有哪些具体避雷点。"
    args_schema: Type[BaseModel] = XhsSearchInput

    server_url: str = "http://117.72.17.28:18060/mcp"

    def _run(self, keyword: str) -> str:
        logger.info(f"[xhs_mcp_skill] 开始检索小红书并获取详情，关键词：{keyword}")

        headers = {"Content-Type": "application/json"}
        bypass_proxy = {"http": None, "https": None}

        # 1. 握手阶段
        init_payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "langchain-agent", "version": "1.0"}},
            "id": 1
        }

        try:
            res_init = requests.post(self.server_url, json=init_payload, headers=headers, proxies=bypass_proxy,
                                     timeout=5)
            session_id = res_init.headers.get("Mcp-Session-Id")
            if not session_id:
                return "小红书检索服务异常：无法获取通信凭证。"

            headers["Mcp-Session-Id"] = session_id
            requests.post(self.server_url, json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                          headers=headers, proxies=bypass_proxy, timeout=5)

            # 2. 执行搜索阶段
            call_payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "search_feeds", "arguments": {"keyword": keyword}},
                "id": 2
            }
            res_call = requests.post(self.server_url, json=call_payload, headers=headers, proxies=bypass_proxy,
                                     timeout=30)
            data = res_call.json()

            # 3. 解析列表
            if "result" in data and "content" in data["result"]:
                raw_text = data["result"]["content"][0]["text"]
                parsed_content = json.loads(raw_text)
                feeds = parsed_content.get("feeds", [])

                if not feeds:
                    return f"未检索到关于 '{keyword}' 的有效笔记。"

                extracted_info = f"为您检索到关于 '{keyword}' 的最新小红书深度笔记：\n\n"

                # 遍历前 3 篇帖子看详情
                for idx, feed in enumerate(feeds[:3]):
                    feed_id = feed.get("id")
                    xsec_token = feed.get("xsecToken")

                    card = feed.get("noteCard", {})
                    title = card.get("displayTitle", "无标题")
                    user = card.get("user", {}).get("nickname", "未知用户")
                    likes = card.get("interactInfo", {}).get("likedCount", "0")

                    extracted_info += f"=== 第 {idx + 1} 篇 ===\n"
                    extracted_info += f"【标题】{title} (作者:{user} | 点赞:{likes})\n"

                    # 🌟 核心修复 1：增加延时，防止触发小红书反爬虫超时拦截
                    if idx > 0:
                        logger.info(f"等待 2.5 秒后抓取第 {idx + 1} 篇详情，防风控...")
                        time.sleep(2.5)

                        # 4. 获取正文详情
                    if feed_id and xsec_token:
                        detail_payload = {
                            "jsonrpc": "2.0",
                            "method": "tools/call",
                            "params": {
                                "name": "get_feed_detail",
                                "arguments": {"feed_id": feed_id, "xsec_token": xsec_token}
                            },
                            "id": 3 + idx
                        }

                        try:
                            # 增加一点宽限时间
                            res_detail = requests.post(self.server_url, json=detail_payload, headers=headers,
                                                       proxies=bypass_proxy, timeout=20)
                            detail_data = res_detail.json()

                            if "result" in detail_data and "content" in detail_data["result"]:
                                detail_raw = detail_data["result"]["content"][0]["text"]
                                detail_json = json.loads(detail_raw)

                                # 🌟 核心修复 2：精准匹配 get_feed_detail 的真实 JSON 结构
                                post_content = ""
                                if "data" in detail_json and "note" in detail_json["data"]:
                                    post_content = detail_json["data"]["note"].get("desc", "")
                                elif "noteCard" in detail_json and "desc" in detail_json["noteCard"]:
                                    post_content = detail_json["noteCard"]["desc"]
                                elif "desc" in detail_json:
                                    post_content = detail_json["desc"]

                                if not post_content:
                                    post_content = str(detail_json)[:300]

                                post_content = post_content.replace("\n", " ")[:400]
                                extracted_info += f"【正文详情】{post_content}...\n\n"
                            else:
                                extracted_info += "【正文详情】未提取到有效内容。\n\n"

                        except requests.exceptions.ReadTimeout:
                            extracted_info += "【正文详情】抓取超时（可能触发风控限制）。\n\n"
                        except Exception as e:
                            extracted_info += f"【正文详情】抓取异常。\n\n"
                    else:
                        extracted_info += "【正文详情】缺少抓取凭证。\n\n"

                logger.info("[xhs_mcp_skill] 数据解析与详情抓取全部完成！")
                return extracted_info
            else:
                return "小红书检索服务返回了无法识别的数据格式。"

        except Exception as e:
            logger.error(f"[xhs_mcp_skill] 运行异常: {str(e)}")
            return f"小红书检索服务暂不可用，请依赖内部知识库。错误: {str(e)}"


# ==========================================
# 本地独立测试模块
# ==========================================
if __name__ == '__main__':
    xhs_skill = XhsMcpSearchSkill()
    print("========== 开始测试究极版小红书 Skill (防风控版) ==========")
    result = xhs_skill.invoke({"keyword": "哈尔滨 美食 避雷"})
    print("\n✅ 喂给大模型的数据现在长这样：\n")
    print(result)