# llm_service.py: 提供与不同 LLM 交互的统一接口。

from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
# 假设您已为您的 LLM 提供商配置了 LangChain 环境变量 (例如 OPENAI_API_KEY)
# 或者您可以在此处显式初始化模型，可能从 config/settings.py 加载
from langchain_openai import ChatOpenAI # 示例提供商，根据 Dify 插件 (grok-beta, chatgpt) 需要进行调整
# from langchain_anthropic import ChatAnthropic # 如果通过 'langgenius/x' 使用 Anthropic 模型
# from langchain_google_genai import ChatGoogleGenerativeAI # 如果使用 Gemini 模型

# --- LLM 初始化 (使用 OpenAI 示例) ---
# TODO: 通过 config/settings.py 使模型选择可配置
# 注意: Dify 使用特定的提供商，如 'langgenius/openai/openai' 和 'langgenius/x/x' (Grok)
# 我们将在这里使用标准的 LangChain 集成。如果需要直接的提供商映射，请进行调整。
llm_gpt4o_mini = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
llm_gpt4o_latest = ChatOpenAI(model="gpt-4o", temperature=0.7) # 假设 'chatgpt-4o-latest' 映射到 gpt-4o

# --- 服务函数 ---

def extract_table_names(schema_json_array: List[str]) -> str:
    """
    使用 LLM 从原始 schema JSON 数组中提取表名。

    对应 Dify 节点 '1742697648839' 的逻辑和提示。

    参数:
        schema_json_array: 来自 /get_schema API 的原始结果 (包含一个 JSON 字符串的列表)。

    返回:
        一个由换行符分隔的表名字符串。
    """
    if not schema_json_array:
        return ""

    # 确保我们使用的是 JSON 字符串内容，而不是列表本身
    context = schema_json_array[0] if schema_json_array else "{}"

    # 基于 Dify 节点 '1742697648839' (gpt-4o-mini) 的提示
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """根据以下从数据库获取的表结构 JSON 数据：{{context}}，提取所有表名，遵循以下规则：

1. 从 JSON 数据中识别所有表名（JSON 对象的顶级键）。
2. 输出纯文本表名列表，每行一个表名，不带任何符号（如引号、花括号、冒号等）。
3. 不添加额外说明或标记（如 ```）。

示例：
- 输入：
{"result": ["{\"tickets\": {\"fields\": {\"ticket_id\": {\"type\": \"varchar(20)\"}}}, \"customers\": {\"fields\": {\"customer_id\": {\"type\": \"int\"}}}}"]}
- 输出：
tickets
customers
"""),
        ("user", "表结构数据：{{context}}")
    ])

    chain = prompt_template | llm_gpt4o_mini | StrOutputParser()

    try:
        result = chain.invoke({"context": context})
        # 基本清理：移除每行潜在的前导/尾随空格，以符合 nl_string_to_list 的预期
        cleaned_result = "\n".join([line.strip() for line in result.strip().split('\n')])
        return cleaned_result
    except Exception as e:
        print(f"调用 LLM 进行 extract_table_names 时出错: {e}")
        # 返回空字符串还是抛出错误？Dify 似乎会继续执行，返回空字符串。
        return ""


def format_schema(schema_json_array: List[str]) -> str:
    """
    使用 LLM 将原始 schema JSON 数组格式化为单个、干净的 JSON 对象字符串。

    对应 Dify 节点 '1742268574820' 的逻辑和提示。

    参数:
        schema_json_array: 来自 /get_schema API 的原始结果 (包含一个 JSON 字符串的列表)。

    返回:
        一个包含单个、格式良好的 JSON 对象字符串，代表 schema。
    """
    if not schema_json_array:
        return "{}" # 如果输入为空，返回空 JSON 对象字符串

    # 确保我们使用的是 JSON 字符串内容
    context = schema_json_array[0] if schema_json_array else "{}"

    # 基于 Dify 节点 '1742268574820' (chatgpt-4o-latest) 的提示
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "你是一个数据结构整理助手。") ,
        ("user", """以下是从数据库获取的原始表结构 JSON 数据（可能是一个数组）：{{context}}

请从数组中提取第一个 JSON 字符串，并确保输出为一个完整的、有效的 JSON 对象，包含所有表结构信息。

注意：
- 输出必须是一个单一的 JSON 对象，格式为 {"table1": {...}, "table2": {...}, ...}。
- 确保每个表定义之间用逗号分隔，且整体用大括号 {} 包裹。
- 不得添加换行符、Markdown 标记（如 ```json）或其他非 JSON 字符。
- 如果输入数据量较大，优先确保 JSON 结构的完整性，避免截断。
- 如果输入无效或无法解析，返回空对象 \"{}\"。
- 在生成 JSON 时，逐表检查，确保每对键值对后添加逗号，最后一表除外。

示例：
- 输入：[{"clazz": {"fields": {...}}, "dept": {"fields": {...}}}]
- 输出：{"clazz": {"fields": {...}}, "dept": {"fields": {...}}}
""")
    ])

    chain = prompt_template | llm_gpt4o_latest | StrOutputParser()

    try:
        result = chain.invoke({"context": context})
        # 清理 LLM 可能添加的潜在 markdown 代码围栏或多余空格
        cleaned_result = result.strip()
        if cleaned_result.startswith("```json"):
            cleaned_result = cleaned_result[7:]
        if cleaned_result.startswith("```"):
             cleaned_result = cleaned_result[3:]
        if cleaned_result.endswith("```"):
            cleaned_result = cleaned_result[:-3]
        cleaned_result = cleaned_result.strip()
        # 确保它看起来像一个基本的 JSON 对象，否则返回空
        if not (cleaned_result.startswith("{") and cleaned_result.endswith("}")):
            print(f"警告: LLM 为 format_schema 的输出看起来不像 JSON: {result}")
            return "{}"
        return cleaned_result
    except Exception as e:
        print(f"调用 LLM 进行 format_schema 时出错: {e}")
        # 出错时返回空 JSON 对象字符串
        return "{}" 