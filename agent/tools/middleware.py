from typing import Callable

from langchain.agents import AgentState
from langchain.agents.middleware import wrap_tool_call, before_model, ModelRequest, dynamic_prompt
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command
from utils.logger_handler import logger
from utils.prompt_loader import load_system_prompts
from utils.prompt_loader import load_report_prompts



# 使用wrap_tool_call装饰器：将普通函数包装为LangChain可识别的工具中间件
@wrap_tool_call
def monitor_tool(
    # 第一个参数：工具调用请求对象，包含工具名称、参数等信息
    request: ToolCallRequest,
    # 第二个参数：真正的工具处理函数，接收请求并返回工具消息或命令
    handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
    """
    工具监控中间件：对所有Agent调用的工具进行统一监控和日志记录
    作用：在工具执行前后自动打印日志，捕获异常，不影响工具本身逻辑
    """
    # 1. 记录工具开始执行的日志
    logger.info(f"[tool monitor]执行工具：{request.tool_call['name']}")
    # 2. 记录传入工具的参数
    logger.info(f"[tool monitor]传入参数：{request.tool_call['args']}")

    try:
        # 3. 执行真正的工具逻辑（调用handler）
        result = handler(request)
        # 4. 执行成功日志
        logger.info(f"[tool monitor]工具{request.tool_call['name']}调用成功")
        # 5. 返回执行结果
        return result
    except Exception as e:
        # 6. 执行失败日志：记录工具名和错误原因
        logger.error(f"[tool monitor]工具{request.tool_call['name']}调用失败，原因：{str(e)}")
        # 7. 重新抛出异常：让上层Agent能感知错误，避免静默失败
        raise e

"""
大模型直接就能识别两个参数，而不用return
"""
@before_model  # LangGraph生命周期钩子：大模型执行生成回答前，自动触发该函数
def log_before_model(
        state: AgentState,          # AgentState 存的是单次对话的动态状态
        runtime: Runtime,           # Agent的运行时上下文：存储执行过程中的动态信息
):         # 模型调用前置日志函数：记录模型输入关键信息，辅助调试/监控
    logger.info(f"[log_before_model]即将调用模型，带有{len(state['messages'])}条消息。")
    logger.debug(f"[log_before_model]{type(state['messages'][-1]).__name__} | {state['messages'][-1].content.strip()}")

    # 3. 返回None：该钩子仅做日志记录，不修改Agent状态/运行时上下文
    return None

"""
识别需不需要我们生成模板，进而让agent表达出不同的的决策
"""
@dynamic_prompt  # 装饰器：标记该函数为「动态提示词切换钩子」，模型生成提示词前自动调用
def report_prompt_switch(request: ModelRequest):  # 动态切换提示词核心函数
    """
    报告场景提示词切换逻辑：根据runtime上下文的"report"标记，动态返回不同的系统提示词
    核心作用：让Agent在「普通问答」和「报告生成」场景使用不同的提示词，适配不同回答风格
    """
    # 1. 从运行时上下文读取"report"标记（默认值为False）
    # request.runtime.context：就是你在agent.stream()中传入的context={"report": False}
    is_report = request.runtime.context.get("report", False)
    if is_report:  # 2. 是报告生成场景：返回报告专用提示词
        return load_report_prompts()
    # 3. 非报告场景：返回默认系统提示词（普通问答）
    return load_system_prompts()