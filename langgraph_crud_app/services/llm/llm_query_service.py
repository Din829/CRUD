# llm_query_service.py: 提供查询/分析流程相关的 LLM 服务。

from typing import List, Optional, Dict, Literal
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import os
import re
import json
from langgraph_crud_app.services import data_processor
from langgraph_crud_app.config import settings # 导入配置

# --- LLM 初始化 ---
print(f"--- Debug: 从 settings 读取 API Key: {'*' * (len(settings.OPENAI_API_KEY) - 8) + settings.OPENAI_API_KEY[-4:] if settings.OPENAI_API_KEY else None} ---") # 打印脱敏密钥
llm_gpt4_1 = ChatOpenAI(
    model="gpt-4.1",
    temperature=0.7, # Keep temperature consistent for now
    
)

# --- 服务函数 ---

def classify_main_intent(query: str) -> str:
    """
    使用 LLM 对用户查询进行主意图分类。
    对应 Dify 节点: '1742268516158' (问题分类器)
    Args:
        query: 用户输入的查询字符串。
    Returns:
        分类结果字符串。
    """
    print(f"---LLM 服务: 分类主意图 (Query: '{query}')---")
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """你是一个智能分类助手。根据用户输入，严格按照以下类别和规则进行分类，只输出最终的类别名称（英文标签）。

类别定义:
1.  **查询/分析 (query_analysis)**: 检索记录或分析数据，含关键词：查询、搜索、查找、查、详情、状态、分析、统计、多少、总数等。示例："查询 TKT-2307-0001 状态""统计工单数量"
2.  **修改 (modify)**: 更改记录，含关键词：修改、更改、变更、更新。示例："修改 TKT-2307-0001 状态为已解决"
3.  **确认/其他 (confirm_other)**: 含关键词：保存、确认、是、好、确定，或无法归类。示例："保存""是""继续"
4.  **重置 (reset)**: 重置或清空，含关键词：重置、重新开始、清空。示例："重置所有数据"
5.  **新增 (add)**: 添加新记录，含关键词：添加、新增、创建（无统计/分析词）。示例："新增一条工单"
6.  **删除 (delete)**: 删除记录，含关键词：删除、移除、取消。示例："删除 TKT-2307-0001"

规则:
- 多特征冲突（如"新增并统计"），优先"查询/分析 (query_analysis)"。
- "新增"若涉统计/分析，归"查询/分析 (query_analysis)"。
- 无法判断，默认"确认/其他 (confirm_other)"。

输出要求：
仅输出分类结果对应的英文标签，例如：query_analysis, modify, confirm_other, reset, add, delete。不要任何其他文字。"""),
        ("user", "用户输入: {query}")
    ])
    chain = prompt_template | llm_gpt4_1 | StrOutputParser()
    try:
        result = chain.invoke({"query": query}).strip().lower()
        valid_intents = ["query_analysis", "modify", "confirm_other", "reset", "add", "delete"]
        cleaned_result = re.sub(r'[^\w_]', '', result)
        if cleaned_result in valid_intents:
            print(f"LLM 分类结果 (主意图): {cleaned_result}")
            return cleaned_result
        else:
            print(f"警告: LLM 主意图分类输出不规范: '{result}'. 回退到默认。")
            if "query" in result or "分析" in result or "查" in result: return "query_analysis"
            if "修改" in result or "更改" in result: return "modify"
            if "新增" in result or "添加" in result: return "add"
            if "删除" in result or "移除" in result: return "delete"
            if "重置" in result or "清空" in result: return "reset"
            return "confirm_other"
    except Exception as e:
        print(f"调用 LLM 进行 classify_main_intent 时出错: {e}")
        return "confirm_other"

def classify_query_analysis_intent(query: str) -> Literal["query", "analysis"]:
    """
    使用 LLM 对查询/分析意图进行子分类。
    对应 Dify 节点: '1743298467743' (查询/分析分类)
    Args:
        query: 用户输入的查询字符串。
    Returns:
        分类结果字符串 ("query" 或 "analysis").
    """
    print(f"---LLM 服务: 分类查询/分析子意图 (Query: '{query}')---")
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """你是一个智能分类助手。根据用户输入的问题，严格按照以下规则将其分类为"查询 (query)"或"分析 (analysis)"，只输出最终的类别名称（英文标签）。

规则:
1.  **查询 (query)**:
    - 用户意图是检索具体记录的完整详细信息（所有字段）。
    - 包含关键词：查询、搜索、查找、查、具体、详情、状态、内容等。
    - 必须涉及特定标识（如 ID、编号）或明确要求完整记录。
    - 示例："查询 TKT-2307-0001 的状态"，"搜索 TKT-2307-0001 的完整信息"，"查询第624号数据"。
2.  **分析 (analysis)**:
    - 用户意图是统计、汇总、分析整体数据，或仅列举标识（不返回完整记录）。
    - 包含关键词：统计、分析、汇总、多少、总数、分布、平均、趋势、比例、查找、列出等。
    - 示例："数据表中一共多少工单"，"统计每个部门的工单数量"，"查找销售部的紧急工单的编号"，"分析紧急工单的分布情况"。

输出要求：
仅输出分类结果对应的英文标签：query 或 analysis。不要任何其他文字。"""),
        ("user", "用户输入: {query}")
    ])
    chain = prompt_template | llm_gpt4_1 | StrOutputParser()
    try:
        result = chain.invoke({"query": query}).strip().lower()
        cleaned_result = re.sub(r'[^\w_]', '', result)
        if cleaned_result == "analysis":
            print("LLM 分类结果 (子意图): analysis")
            return "analysis"
        elif cleaned_result == "query":
            print("LLM 分类结果 (子意图): query")
            return "query"
        else:
            print(f"警告: LLM 查询/分析子意图分类输出不规范: '{result}'. 回退到默认 'query'。")
            if "分析" in query or "统计" in query or "多少" in query or "总数" in query:
                return "analysis"
            return "query"
    except Exception as e:
        print(f"调用 LLM 进行 classify_query_analysis_intent 时出错: {e}")
        return "query"

def generate_select_sql(query: str, schema: str, table_names: List[str], data_sample: str) -> str:
    """
    使用 LLM 根据用户问题和数据库元数据生成 SELECT SQL 查询。
    对应 Dify 节点: '1742268678777' (mySQL SELECT 查询)
    Args:
        query: 用户输入的查询字符串。
        schema: 格式化的数据库 Schema JSON 字符串。
        table_names: 数据库中的表名列表。
        data_sample: 数据库表的数据示例 JSON 字符串。
    Returns:
        生成的 SELECT SQL 查询语句，或者在无法生成时返回特定错误消息。
    """
    print(f"---LLM 服务: 生成 SELECT SQL (Query: '{query}')---")
    prompt_template = ChatPromptTemplate.from_messages([
         ("system", """你是一个数据库查询助手。根据用户问题、表结构、表名列表和数据示例生成一个合法的 MySQL SELECT 查询语句。

重要规则：
1.  **表和字段**: 严格使用提供的表结构中的表和字段。表名列表提供了所有可用表。
2.  **输出格式**: 只输出完整的、单行的 SQL 语句，不包含任何注释、换行符或 ```sql 标记。
3.  **值引用**: 字符串值必须使用单引号包裹，数值不加引号。
4.  **多表查询 (JOIN)**: 如果用户查询明显涉及多个实体（例如 \"员工和他们的工作经历\"），根据表结构中的外键关系（`foreign_keys` 字段）使用 `LEFT JOIN` 关联相关表。主表基于用户问题的主要实体确定。别名应简洁（例如 `e` 代表 `emp`, `d` 代表 `dept`）。
5.  **ID/编号处理**:
    *   从表结构中动态识别主键字段（通常是第一个字段或标记为 '主键'）。注意其数据类型（例如 `varchar(9)` 或 `int`)。
    *   参考数据示例中的主键格式（例如前缀 'REP' 和总长度 9 -> 'REP000001'）。
    *   **精确匹配**: 如果用户输入完整的编号（例如 'REP000777'），直接在 `WHERE` 子句中使用该值进行精确匹配。
    *   **部分数字匹配**: 如果用户输入类似 \"第 X 号数据\" 或纯数字 X（例如 \"查询第 647 号数据\" 或 \"647\"）：
        *   提取数字 X。
        *   参考数据示例中的主键值格式（例如 'REP000001'）：
            *   如果主键是 `varchar` 类型且有前缀，将 X 左侧补零填充至总长度减去前缀长度，然后拼接前缀（例如 647 -> '000647' -> 'REP000647'）。
            *   如果主键是 `varchar` 类型但无前缀，将 X 左侧补零填充至字段总长度（例如 647, 长度 9 -> '000000647'）。
            *   如果主键是 `int` 或类似数值类型，直接使用数字 X。
        *   在 `WHERE` 子句中使用生成的值进行匹配。
6.  **模糊或无效查询**: 如果用户输入过于模糊、信息不足以定位具体表/字段，或者无法根据规则生成有效 SQL，固定返回字符串：\"ERROR: 请澄清你的查询条件，例如提供完整编号或指定具体字段。\"

可用信息:
-   表名列表: {table_names_str}
-   表结构 (JSON): {schema}
-   数据示例 (JSON): {data_sample}"""),
        ("user", "用户问题: {query}")
    ])
    chain = prompt_template | llm_gpt4_1 | StrOutputParser()
    try:
        table_names_str = ", ".join(table_names)
        try: json.loads(schema)
        except json.JSONDecodeError: schema = "{}"
        try: json.loads(data_sample)
        except json.JSONDecodeError: data_sample = "{}"
        result = chain.invoke({
            "query": query, "schema": schema,
            "table_names_str": table_names_str, "data_sample": data_sample
        }).strip()
        if result == "ERROR: 请澄清你的查询条件，例如提供完整编号或指定具体字段。":
            print("LLM 请求澄清查询条件。")
            return result
        elif "ERROR:" in result:
             print(f"LLM 生成 SELECT SQL 时返回错误: {result}")
             return "ERROR: 请澄清你的查询条件，例如提供完整编号或指定具体字段。"
        if not result.upper().startswith("SELECT"):
            print(f"警告: LLM 生成的 SELECT SQL 看起来无效: '{result}'. 请求澄清。")
            return "ERROR: 请澄清你的查询条件，例如提供完整编号或指定具体字段。"
        print(f"LLM 生成的 SELECT SQL: {result}")
        return result
    except Exception as e:
        print(f"调用 LLM 进行 generate_select_sql 时出错: {e}")
        return "ERROR: 请澄清你的查询条件，例如提供完整编号或指定具体字段。"

def generate_analysis_sql(query: str, schema: str, table_names: List[str], data_sample: str) -> str:
    """
    使用 LLM 根据用户问题和数据库元数据生成分析 SQL 查询 (聚合, GROUP BY 等)。
    对应 Dify 节点: '1743298593001' (Mysql 分析语句编辑)
    Args:
        query: 用户输入的查询字符串。
        schema: 格式化的数据库 Schema JSON 字符串。
        table_names: 数据库中的表名列表。
        data_sample: 数据库表的数据示例 JSON 字符串。
    Returns:
        生成的分析 SQL 查询语句，或者在无法生成时返回特定错误消息。
    """
    print(f"---LLM 服务: 生成分析 SQL (Query: '{query}')---")
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """你是一个数据库分析助手。根据用户问题、表结构、表名列表和数据示例生成一个合法的 MySQL 分析语句（例如使用 COUNT, AVG, SUM, GROUP BY 等）。

重要规则：
1.  **表和字段**: 严格使用提供的表结构中的表和字段。表名列表提供了所有可用表。
2.  **输出格式**: 只输出完整的、单行的 SQL 语句，不包含任何注释、换行符或 ```sql 标记。
3.  **分析重点**: 确保生成的 SQL 是用于分析或聚合的，而不是简单的记录检索。
4.  **多表查询 (JOIN)**: 如果用户分析需求明显涉及多个实体（例如 \"统计每个部门的员工数\"），根据表结构中的外键关系（`foreign_keys` 字段）使用 `LEFT JOIN` 关联相关表。
5.  **模糊或无效查询**: 如果用户输入无法明确对应到分析操作（例如只是简单问候），或者无法根据信息生成有效的分析 SQL，固定返回字符串：\"ERROR: 请澄清你的分析需求，例如'统计每个部门的员工数'。\"

可用信息:
-   表名列表: {table_names_str}
-   表结构 (JSON): {schema}
-   数据示例 (JSON): {data_sample}"""),
        ("user", "用户问题: {query}")
    ])
    chain = prompt_template | llm_gpt4_1 | StrOutputParser()
    try:
        table_names_str = ", ".join(table_names)
        try: json.loads(schema)
        except json.JSONDecodeError: schema = "{}"
        try: json.loads(data_sample)
        except json.JSONDecodeError: data_sample = "{}"
        result = chain.invoke({
            "query": query, "schema": schema,
            "table_names_str": table_names_str, "data_sample": data_sample
        }).strip()
        if result == "ERROR: 请澄清你的分析需求，例如'统计每个部门的员工数'。":
            print("LLM 请求澄清分析需求。")
            return result
        elif "ERROR:" in result:
             print(f"LLM 生成分析 SQL 时返回错误: {result}")
             return "ERROR: 请澄清你的分析需求，例如'统计每个部门的员工数'。"
        analysis_keywords = ["COUNT(", "AVG(", "SUM(", "MAX(", "MIN(", "GROUP BY"]
        if not any(keyword in result.upper() for keyword in analysis_keywords):
            print(f"警告: LLM 生成的分析 SQL 看起来不像分析语句: '{result}'. 请求澄清。")
            return "ERROR: 请澄清你的分析需求，例如'统计每个部门的员工数'。"
        print(f"LLM 生成的分析 SQL: {result}")
        return result
    except Exception as e:
        print(f"调用 LLM 进行 generate_analysis_sql 时出错: {e}")
        return "ERROR: 请澄清你的分析需求，例如'统计每个部门的员工数'。"

def format_query_result(query: str, sql_result_str: str) -> str:
    """
    使用 LLM 将 SQL 查询结果 (JSON 字符串) 格式化为面向用户的友好回复。
    对应 Dify 节点: '1742434616785' (LLM 6)

    Args:
        query: 原始用户查询。
        sql_result_str: 来自 API 的 SQL 查询结果 (JSON 字符串)。

    Returns:
        格式化后的用户回复字符串。
    """
    print(f"---LLM 服务: 格式化查询结果 (Query: '{query}')---")
    # Adapting Dify prompt for formatting query results
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """你是一个结果展示助手。请将提供的 JSON 数据内容，针对用户的原始问题，整理成易于阅读的格式输出给用户。

规则：
1.  理解用户问题的意图，选择 JSON 数据中的相关字段进行展示。
2.  如果结果包含多条记录 (JSON 数据是一个列表，包含多个对象)，按记录分段展示，每段以 \"记录 X:\" 开头（X 为序号，从 1 开始）。
3.  对于单条记录或每条记录内部，使用 \"字段名: 字段值\" 的格式清晰展示，每对占一行。
4.  避免输出原始 JSON 格式或任何代码标记。
5.  如果数据为空或无效 (例如输入是空列表 \"[]\" 或空字符串)，返回："根据您的查询，没有找到具体数据。"。
6.  输出为纯文本。"""),
        ("user", "原始问题: {query}\n查询结果 (JSON String): {sql_result}")
    ])

    chain = prompt_template | llm_gpt4_1 | StrOutputParser()

    try:
        # Basic check if input string represents an empty list JSON
        if data_processor.is_query_result_empty(sql_result_str):
             return "根据您的查询，没有找到具体数据。"

        result = chain.invoke({
            "query": query,
            "sql_result": sql_result_str
        }).strip()
        print(f"LLM 格式化后的查询结果:\n{result}")
        return result
    except Exception as e:
        print(f"调用 LLM 进行 format_query_result 时出错: {e}")
        # Fallback message if formatting fails
        return f"查询成功，但格式化结果时遇到问题。原始结果: {sql_result_str}"


def analyze_analysis_result(query: str, sql_result_str: str, schema: str, table_names: List[str]) -> str:
    """
    使用 LLM 分析 SQL 分析查询的结果 (JSON 字符串)，并生成包含洞察和建议的报告。
    对应 Dify 节点: '1743298860520' (结果分析)

    Args:
        query: 原始用户查询。
        sql_result_str: 来自 API 的 SQL 分析结果 (JSON 字符串)。
        schema: 格式化的数据库 Schema JSON 字符串。
        table_names: 数据库中的表名列表。

    Returns:
        包含分析、洞察和建议的用户回复字符串。
    """
    print(f"---LLM 服务: 分析分析结果 (Query: '{query}')---")
     # Adapting Dify prompt for analyzing analysis results
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """你是一个数据分析报告助手。根据用户问题、分析型 SQL 的查询结果 (JSON 格式)、数据库表结构和表名，生成一份简洁易懂的分析报告。

报告应包含：
1.  **结果总结**: 以清晰的方式（例如纯文本表格或列表）展示查询结果的关键数据。字段名应易于理解（可参考表结构）。
2.  **洞察与发现**:
    *   识别数据中的主要趋势（例如，增长/下降，时间模式）。
    *   指出任何显著的异常或与其他数据的明显差异（例如，某个类别的数量远超其他）。
3.  **简要建议 (可选)**: 如果适用，根据洞察提供一两项简洁、可操作的建议（例如，"关注 XX 类别"，"建议优化 YY 指标"）。

规则：
-   参考用户问题理解分析的重点。
-   输出为纯文本，不要使用 Markdown 或代码块。
-   如果结果为空或无效，直接说明"根据您的分析请求，没有获得有效数据。"。
-   洞察和建议部分以"-"开头，简洁明了。

可用信息:
- 表结构: {schema}
- 表名: {table_names_str}
- 分析结果 (JSON String): {sql_result}"""),
        ("user", "用户问题: {query}")
    ])

    chain = prompt_template | llm_gpt4_1 | StrOutputParser()

    try:
        # Basic check if input string represents an empty list JSON
        if data_processor.is_query_result_empty(sql_result_str):
             return "根据您的分析请求，没有获得有效数据。"

        table_names_str = ", ".join(table_names)
        try: json.loads(schema)
        except json.JSONDecodeError: schema = "{}"

        result = chain.invoke({
            "query": query,
            "sql_result": sql_result_str,
            "schema": schema,
            "table_names_str": table_names_str
        }).strip()
        print(f"LLM 生成的分析报告:\n{result}")
        return result
    except Exception as e:
        print(f"调用 LLM 进行 analyze_analysis_result 时出错: {e}")
        return f"分析查询成功，但生成报告时遇到问题。原始结果: {sql_result_str}"

# TODO: Add format_query_result and analyze_analysis_result functions later 