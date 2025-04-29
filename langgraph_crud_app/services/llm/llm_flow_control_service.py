"""
封装与主流程控制相关的 LLM 调用逻辑。
例如：判断 Yes/No、格式化 API 结果等。
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from typing import Literal, Dict, Any
import json

from langgraph_crud_app.config import settings

# 可以在这里添加后续的 LLM 服务函数 

def classify_yes_no(query: str) -> Literal["yes", "no", "unknown"]:
    """
    使用 LLM 判断用户输入是肯定 ("yes") 还是否定 ("no") 或无法判断 ("unknown")。
    对应 Dify 节点: '1742350663522' (是/否分类器)
    """
    print(f"---LLM 服务: 判断 Yes/No, 输入: '{query}'---")
    # 简化版 Prompt，模仿 Dify 逻辑
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "你是一个简单的意图分类器。根据用户输入，判断其意图是肯定还是否定。如果用户的意图是肯定的（例如 '是'、'好的'、'确认'、'保存'），输出 'yes'。如果用户的意图是否定的（例如 '否'、'取消'、'不行'），输出 'no'。如果无法明确判断或用户输入无关内容，输出 'unknown'。只输出 'yes'、'no' 或 'unknown' 中的一个词。" ),
        ("user", "用户输入：{query}")
    ])

    # 使用配置的模型
    # llm = ChatOpenAI(model=settings.MODEL_NAME, temperature=settings.TEMPERATURE)
    # TODO: 从 settings 加载模型和温度，目前暂时硬编码
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    chain = prompt_template | llm

    try:
        response = chain.invoke({"query": query})
        result = response.content.strip().lower()
        print(f"LLM Yes/No 判断结果: {result}")
        if result == "yes":
            return "yes"
        elif result == "no":
            return "no"
        else:
            return "unknown"
    except Exception as e:
        print(f"LLM Yes/No 判断失败: {e}")
        return "unknown" # 出错时默认为 unknown 

def format_api_result(result: Any, original_query: str, operation_type: str) -> str:
    """
    使用 LLM 根据 API 调用结果和原始请求生成用户友好的回复。
    对应 Dify 节点: '1744661636396' (修改结果返回), '1744932857138' (新增结果返回), '1744933370451' (删除结果返回)
    """
    print(f"---LLM 服务: 格式化 API 结果, 操作类型: {operation_type}, 结果: {result}---")

    # 准备上下文信息
    context = f"操作类型：{operation_type}\n原始用户请求：{original_query}\nAPI 调用结果：{json.dumps(result, ensure_ascii=False)}"

    # 构建 Prompt，模仿 Dify 逻辑
    # Dify Prompt: "根据{{#context#}}的结果，和用户提问{{#sys.query#}}输出自然语言相关结果信息。 ... 这个就是返回相关id修改成功的信息，之后提示用户请在数据库确认结果 ... 如果输出错误信息，则解析后输出"
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", f"你是一个友好的助手。根据提供的 API 调用结果和用户之前的请求，生成一段自然语言回复。主要任务是告知用户 {operation_type} 操作是否成功，如果成功，简洁地总结结果并提示用户可以在数据库确认；如果失败，清晰地说明错误信息。不要包含任何原始 API 结果的 JSON 细节，除非错误信息本身就是文本。语言要自然，避免模板化。" ),
        ("user", "请根据以下信息生成回复：\n\n{context}")
    ])

    # 使用配置的模型 (同样，暂时硬编码)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    chain = prompt_template | llm

    try:
        response = chain.invoke({"context": context})
        formatted_result = response.content.strip()
        print(f"LLM 格式化结果: {formatted_result}")
        return formatted_result
    except Exception as e:
        print(f"LLM 格式化 API 结果失败: {e}")
        # LLM 调用失败时的备用逻辑
        if isinstance(result, list) and any("error" in item for item in result):
             first_error = next((item["error"] for item in result if "error" in item), "未知错误")
             return f"{operation_type} 操作似乎遇到了一些问题：{first_error} 请检查您的输入或联系管理员。"
        elif isinstance(result, dict) and "error" in result:
             return f"{operation_type} 操作失败：{result['error']} 请检查您的输入或联系管理员。"
        elif result:
             # 简单的成功消息
             return f"{operation_type} 操作已成功执行。您可以在数据库中确认结果。"
        else:
            return f"{operation_type} 操作已执行，但未收到明确的成功或失败信息。" 