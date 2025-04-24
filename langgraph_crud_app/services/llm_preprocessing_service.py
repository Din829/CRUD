# llm_preprocessing_service.py: 提供前置初始化流程相关的 LLM 服务。

from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import os
import re
import json

# --- LLM 初始化 ---
# 警告: 不推荐硬编码 API 密钥。请考虑使用环境变量或其他安全方法。
llm_gpt4_1 = ChatOpenAI(
    model="gpt-4.1",
    temperature=0.7, # Keep temperature consistent for now
    
)

# --- 服务函数 ---

def extract_table_names(schema_json_array: List[str]) -> str:
    """
    使用 LLM 从原始 schema JSON 数组中提取表名。
    对应 Dify 节点 '1742697648839' 的逻辑和提示。
    Args:
        schema_json_array: 来自 /get_schema API 的原始结果。
    Returns:
        一个由换行符分隔的表名字符串。
    """
    if not schema_json_array:
        return ""
    context = schema_json_array[0] if schema_json_array else "{}"
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "你的任务是从给定的 JSON 字符串中提取所有顶级键。这些顶级键代表数据库表名。"),
        ("user", "这是 JSON 字符串: \n{context}\n请提取所有顶级键（表名），每行一个，只输出纯文本表名，不要任何其他文字或标记。")
    ])
    chain = prompt_template | llm_gpt4_1 | StrOutputParser()
    try:
        result = chain.invoke({"context": context})
        cleaned_result = "\n".join([line.strip() for line in result.strip().split('\n')])
        if "抱歉" in cleaned_result or "无法" in cleaned_result or not cleaned_result:
             print(f"警告: LLM extract_table_names 未能提取有效表名，返回: {cleaned_result}")
             return ""
        return cleaned_result
    except Exception as e:
        print(f"调用 LLM 进行 extract_table_names 时出错: {e}")
        return ""

def format_schema(schema_json_array: List[str]) -> str:
    """
    使用 LLM 将原始 schema JSON 数组格式化为单个、干净的 JSON 对象字符串。
    对应 Dify 节点 '1742268574820' 的逻辑和提示。
    Args:
        schema_json_array: 来自 /get_schema API 的原始结果。
    Returns:
        一个包含单个、格式良好的 JSON 对象字符串，代表 schema。
    """
    if not schema_json_array:
        return "{}"
    context = schema_json_array[0] if schema_json_array else "{}"
    template = """输入是一个 JSON 字符串: {context}
请将这个输入的 JSON 字符串原样输出，确保它是一个有效的 JSON 对象。不要添加任何其他文字或标记。如果输入无效或无法处理，输出空 JSON 对象字符串 {{}}。"""
    prompt_template = PromptTemplate.from_template(template)
    chain = prompt_template | llm_gpt4_1 | StrOutputParser()
    try:
        result = chain.invoke({"context": context})
        cleaned_result = result.strip()
        if cleaned_result.startswith("```json"):
            cleaned_result = cleaned_result[7:]
        if cleaned_result.startswith("```"):
             cleaned_result = cleaned_result[3:]
        if cleaned_result.endswith("```"):
            cleaned_result = cleaned_result[:-3]
        cleaned_result = cleaned_result.strip()
        if not (cleaned_result.startswith("{") and cleaned_result.endswith("}")):
            print(f"警告: LLM 为 format_schema 的输出看起来不像 JSON: {result}")
            return "{}"
        return cleaned_result
    except Exception as e:
        print(f"调用 LLM 进行 format_schema 时出错: {e}")
        return "{}" 