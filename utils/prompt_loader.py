"""
加载提示词模板

main_prompt 是基础规则，定调 Agent 该 “怎么做事”；
rag_summarize_prompt 是数据加工，把零散的检索结果变成有用的信息；
report_prompt 是格式输出，把加工后的信息变成符合要求的结构化报告。
"""
from utils.config_handler import prompts_conf
from utils.path_tool import get_abs_path
from utils.logger_handler import logger


def load_system_prompts() -> str:
    """
    加载主系统提示词模板：
    将 4 个阶段的 prompt 组装成一个完整的超级管家大脑，大模型会根据上下文自主判断当前处于哪个阶段。
    """
    # 按照业务流转顺序排列你的 4 个阶段文件
    phase_files = [
        "prompts/phase1_explore.txt",
        "prompts/phase2_plan.txt",
        "prompts/phase3_feedback.txt",
        "prompts/report_prompt.txt"  # 你的阶段四总结报告
    ]

    # 设定一个全局的总基调
    full_prompt = (
        "你是全网最贴心的「一站式傻瓜旅游管家」。"
        "以下是你的【四阶段核心执行准则】，请根据用户当前的聊天意图和进度，"
        "自主判断当前处于哪个阶段，并严格执行该阶段对应的准则：\n\n"
    )

    for phase_file in phase_files:
        try:
            path = get_abs_path(phase_file)
            with open(path, "r", encoding="utf-8") as f:
                # 将每个阶段的文本拼接起来，并用明显的分隔符隔开，帮助大模型区分层级
                full_prompt += f.read() + "\n\n" + "=" * 50 + "\n\n"
        except Exception as e:
            logger.error(f"[load_system_prompts]拼接提示词时，解析 {phase_file} 出错: {str(e)}")
            raise e

    logger.info("[load_system_prompts]成功将 4 个阶段提示词组装为全局 SOP 大脑。")
    return full_prompt


def load_rag_prompts() -> str:
    """加载RAG总结提示词模板"""
    try:
        rag_summarize_prompt_path = get_abs_path(prompts_conf["rag_summarize_prompt_path"])
    except KeyError as e:
        logger.error(f"[load_rag_summarize_prompts]在yaml配置项中没有rag_summarize_prompt_path配置项")
        raise e

    try:
        with open(rag_summarize_prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"[load_rag_summarize_prompts]解析RAG总结提示词出错: {str(e)}")
        raise e


def load_report_prompts() -> str:
    """加载报告生成提示词模板"""
    try:
        report_prompt_path = get_abs_path(prompts_conf["report_prompt_path"])
    except KeyError as e:
        logger.error(f"[load_report_prompts]在yaml配置项中没有report_prompt_path配置项")
        raise e

    try:
        with open(report_prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"[load_report_prompts]解析报告生成提示词出错: {str(e)}")
        raise e

