"""
封装与处理用户修改请求相关的 LLM 调用逻辑。
"""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from typing import List, Dict, Any, Optional
import json # 新增导入
import re # 新增导入

from langgraph_crud_app.config import settings
from langgraph_crud_app.graph.state import GraphState # 可能需要访问状态

# --- 修改意图解析服务 ---

def _escape_json_for_prompt(json_str: str) -> str:
    """
    转义 JSON 字符串中的大括号，以防止与 LangChain 模板变量冲突。
    """
    if not json_str:
        return "{}"
    # 将单大括号替换为双大括号
    escaped = json_str.replace("{", "{{").replace("}", "}}")
    return escaped

def parse_modify_request(
    query: str,
    schema_str: Optional[str],
    table_names: Optional[List[str]],
    data_sample_str: Optional[str],
    modify_context_result_str: Optional[str] # 新增参数：上下文查询结果
) -> str:
    """
    使用 LLM 解析用户的修改请求，结合上下文查询结果，提取目标表、主键、值和更新字段。
    返回: 预期为包含修改信息的 JSON 字符串。
    """
    print(f"---LLM 服务: 解析修改请求, 输入查询: '{query}'---")

    if not all([schema_str, table_names, data_sample_str]):
        print("错误：缺少必要的数据库元数据 (Schema, 表名, 数据示例)。")
        return '[]'

    # 转义 JSON 数据中的大括号
    escaped_schema = _escape_json_for_prompt(schema_str)
    escaped_sample = _escape_json_for_prompt(data_sample_str)
    table_names_str = str(table_names)
    escaped_tables = _escape_json_for_prompt(table_names_str)
    # 新增：转义上下文查询结果
    escaped_context_result = _escape_json_for_prompt(modify_context_result_str if modify_context_result_str else "[]")

    # 构建 system 和 user 消息
    system_prompt = """你是一个专业的数据库修改助手。你的任务是根据用户输入的自然语言请求，结合提供的数据库表结构、表名列表、数据示例以及实际查询到的记录当前状态，准确地提取出用户想要执行的修改操作信息。"""

    user_prompt = f"""规则：
1. 解析用户输入和查询到的记录当前状态，支持单表或多表修改。
2. 根据表结构、数据示例和查询结果，推断主键和外键关系，确保字段分配到正确表。
3. 区分修改类型：
   - 更新：若查询结果中存在表记录（如 emp.id=46），包含主键（如 {{"primary_key": "id", "primary_value": "46"}}）和修改字段。
   - 新增：若查询结果为空或表未在查询结果中出现，视为新增，仅包含字段，不指定主键，交给后端自动生成。
4. 主键变更支持：
   - 若用户指定主键变更（如"将 dish id=58 改为 61"），输出：
     - {{"primary_key": 主键字段名（如 "id"）}}。
     - {{"primary_value": 原始主键值（如 "58"）}}。
     - {{"target_primary_value": 目标主键值（如 "61"）}}。
   - 非主键字段变更直接放入 {{"fields"}}。
5. 支持基于查询结果的数值计算：
   - 若输入涉及数值字段增减（如"价格增加 3.00"），从查询结果提取当前值，计算后保留字段精度。
   - 查询结果中的数值可能是字符串，需转换为数值计算。
6. 支持时间字段使用 {{"now()"}} 表示当前时间。
7. 输出格式：
   - {{"table_name": [{{"primary_key": "字段名", "primary_value": "原始值", "target_primary_value": "目标值（可选）", "fields": {{"字段": "值", ...}}}}], ...}}
   - 若无主键变更，"target_primary_value" 为空字符串。
   - 新增记录省略 "primary_key" 和 "primary_value"。
8. 若查询结果为空（"[]"），根据用户输入生成新增记录。
9. 输出纯 JSON，无重复键，确保合法性。

输出规则：
- 使用 <output> 标签和代码块格式（```），代码块内容为纯 JSON 文本，无 Markdown 符号。
- 整个输出在 <output> 标签内。

可用信息：
表结构 (Schema): {escaped_schema}
表名列表: {escaped_tables}
数据示例: {escaped_sample}
查询结果 (当前记录状态): {escaped_context_result}

示例：
1. 输入："将部门'学工部'（id=1）的名称改为'学生事务部'，并同步更新所有相关员工到'人事部'（id=5）"
   查询结果：[{{"table_name": "dept", "id": "1", "field1": "学工部"}}, {{"table_name": "emp", "id": "6", "field1": "1"}}]
   输出：
<output>
{{"dept": [{{"primary_key": "id", "primary_value": "1", "target_primary_value": "", "fields": {{"name": "学生事务部"}}}}], "emp": [{{"primary_key": "id", "primary_value": "6", "target_primary_value": "", "fields": {{"dept_id": "5"}}}}]}}
</output>

2. 输入："将菜品 id=58 改为 61，id=59 改为 62"
   查询结果：[{{"table_name": "dish", "id": "58"}}, {{"table_name": "dish", "id": "59"}}]
   输出：
<output>
{{"dish": [{{"primary_key": "id", "primary_value": "58", "target_primary_value": "61", "fields": {{}}}}, {{"primary_key": "id", "primary_value": "59", "target_primary_value": "62", "fields": {{}}}}]}}
</output>

请根据上述规则，处理以下用户请求：
用户请求：{query}

"""


    # 使用配置的模型
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

    try:
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        llm_output = response.content.strip()
        print(f"LLM 解析修改结果 (原始): {llm_output}")

        # 清理 Markdown 和 XML 标签
        if llm_output.startswith("<output>"):
            llm_output = llm_output[len("<output>"):]
        if llm_output.endswith("</output>"):
            llm_output = llm_output[:-len("</output>")]
        llm_output = llm_output.strip() # 清理标签后的空白

        if llm_output.startswith("```json"):
            llm_output = llm_output[7:]
        if llm_output.endswith("```"):
            llm_output = llm_output[:-3]
        llm_output = llm_output.strip()

        # 基本检查 (修正：检查是否为 JSON 对象格式)
        if not llm_output.startswith("{") or not llm_output.endswith("}"):
            print("LLM 输出格式不符合预期的 JSON 对象格式，返回空列表。")
            return "[]"

        try:
            # 尝试解析 JSON
            json.loads(llm_output)
        except json.JSONDecodeError as json_err:
            print(f"LLM 输出无法解析为 JSON: {json_err}，尝试修复特殊格式。")

            # 尝试修复特殊格式
            fixed_output = llm_output
            # 替换 {"now()"} 为 "NOW()"
            fixed_output = re.sub(r'{"now\(\)"}', '"NOW()"', fixed_output)
            # 替换其他可能的函数调用格式
            fixed_output = re.sub(r'{"\s*([^"]+\(\))\s*"}', r'"\1"', fixed_output)

            # 尝试解析修复后的 JSON
            try:
                json.loads(fixed_output)
                print(f"成功修复 JSON 格式问题。")
                return fixed_output
            except json.JSONDecodeError as e:
                print(f"修复后仍无法解析 JSON: {e}，返回空列表。")
                return "[]"

        return llm_output

    except Exception as e:
        print(f"LLM 解析修改请求失败: {e}")
        return "[]"


# --- 错误格式化服务 (可选) ---

# 将在此处添加 format_modify_error 函数 (如果需要)


# --- 新增：用于获取修改上下文的 SQL 生成服务 ---

def generate_modify_context_sql(
    query: str,
    schema_str: Optional[str],
    table_names: Optional[List[str]],
    data_sample_str: Optional[str]
) -> str:
    """
    使用 LLM 根据用户修改请求生成 SELECT SQL，用于查询相关记录的当前状态。
    对应 Dify 节点: '1743630621023'
    返回: SELECT SQL 语句字符串，或空字符串表示失败。
    """
    print(f"---LLM 服务: 生成修改上下文查询 SQL, 输入查询: '{query}'---")

    if not all([schema_str, table_names, data_sample_str]):
        print("错误：缺少必要的数据库元数据 (Schema, 表名, 数据示例)。")
        return ""

    # 转义 JSON 数据中的大括号 (遵循规范)
    escaped_schema = _escape_json_for_prompt(schema_str)
    escaped_sample = _escape_json_for_prompt(data_sample_str)
    # table_names 是列表，先转字符串再转义
    table_names_str = str(table_names)
    escaped_tables = _escape_json_for_prompt(table_names_str)

    # 构建 system 和 user 消息 (遵循 Dify Prompt)
    system_prompt = """根据用户输入和表结构，生成针对单表或多表"查询"的 MySQL SELECT 语句。（不用负责修改或更新部分，仅查询用户问题涉及的领域）"""

    user_prompt = f"""用户输入{query}
表结构{escaped_schema}
表名{escaped_tables}
数据示例（参考）{escaped_sample}

规则：
1. 识别涉及的表和主键（如 dept.id, emp.id）。
2. 如果输入涉及多表修改（如"将 dept id=1 的 name 改为 X，并同步 emp 到 dept_id=Y"），生成单条查询：
   - 使用 UNION ALL 合并多表查询。
   - 每张表返回固定列：'表名' AS table_name, 主键 AS id, 涉及的修改字段，其他列用 NULL 填充至固定列数（如 5 列）。
3. 输出字段：
   - table_name：表名字符串。
   - id：主键值。
   - field1, field2：用户输入中涉及的修改字段（如 name, phone），若无则用 NULL。
   - extra：额外列，用 NULL 填充，确保列数一致。
4. 仅生成单条完整 SQL，不包含分号分隔的多语句，不加注释或换行符。
5. 示例：
① 输入："将部门'学工部'（id=1）的名称改为'学生事务部'，并同步更新所有相关员工到'人事部'（id=5）"
   输出：SELECT 'dept' AS table_name, id, name AS field1, NULL AS field2, NULL AS extra FROM dept WHERE id = 1 UNION ALL SELECT 'emp' AS table_name, id, dept_id AS field1, NULL AS field2, NULL AS extra FROM emp WHERE dept_id = 1
"""

    # 使用配置的模型 (可以和 parse_modify_request 使用同一个，或单独配置)
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

    try:
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        llm_output = response.content.strip() # 获取 LLM 的原始输出
        print(f"LLM 生成上下文 SQL (原始):\n{llm_output}") # 打印完整原始输出以便调试

        # --- 增强 SQL 提取逻辑 ---
        sql_query = ""
        # 尝试用正则表达式查找 ```sql ... ``` 块
        sql_match = re.search(r"```sql\s*(.*?)\s*```", llm_output, re.DOTALL | re.IGNORECASE)

        if sql_match:
            sql_query = sql_match.group(1).strip()
            print(f"通过 Regex 提取到 SQL: {sql_query}")
        else:
            # 如果正则匹配失败，尝试假设整个输出（去除标签后）就是 SQL (作为后备)
            cleaned_output = llm_output
            if cleaned_output.startswith("```"):
                 cleaned_output = cleaned_output[3:]
            if cleaned_output.endswith("```"):
                 cleaned_output = cleaned_output[:-3]
            cleaned_output = cleaned_output.strip()

            # 检查后备方案是否看起来像 SQL
            if cleaned_output.upper().startswith("SELECT"):
                 print("警告：未找到 ```sql 块，尝试使用清理后的整个输出作为 SQL。")
                 sql_query = cleaned_output
            else:
                 print("错误：无法从 LLM 输出中可靠提取 SQL 语句。")
                 return "" # 提取失败，返回空

        # 进一步清理，移除潜在的换行符和多余空格
        sql_query = ' '.join(sql_query.split()).strip()

        # 基本检查 SQL 合法性 (仅检查是否以 SELECT 开头)
        if not sql_query.upper().startswith("SELECT"):
            print("提取或处理后的结果不是有效的 SELECT 语句。")
            return ""

        print(f"LLM 生成上下文 SQL (最终提取): {sql_query}")
        return sql_query

    except Exception as e:
        print(f"LLM 生成上下文 SQL 失败: {e}")
        return ""

# --- 新增：检查直接修改 ID 意图的函数 ---

def check_for_direct_id_modification_intent(query: str) -> Optional[str]:
    """
    使用 LLM 判断用户查询是否包含明确、直接修改主键 ID 的意图。

    Args:
        query: 用户的原始查询字符串。

    Returns:
        如果检测到不允许的意图，返回用户提示字符串；否则返回 None。
    """
    # 构建 Prompt
    # 设计思路：明确任务，强调区分主键修改与其他涉及 ID 的操作，要求简单明确的输出。
    # 使用与 parse_modify_request 相同的 ChatPromptTemplate 方式
    system_prompt = """你是一个高度精确的意图分析助手。你的任务是判断用户查询是否包含 **明确且直接地要求将某个现有记录的主键 ID 值更改为另一个具体值** 的意图。"""
    user_prompt = """请仔细分析以下用户查询：
```
{query}
```

请特别注意区分以下情况，这些情况 **不应** 被视为明确修改主键 ID：
- 使用 ID 来查找或筛选记录（例如："更新 ID 为 5 的订单状态"）。
- 更新记录的其他非 ID 字段的值。
- 修改记录之间的关联关系（外键）（例如："将工单分配给 ID 为 10 的技术员"）。
- 涉及 ID 但意图不明确或模糊的表述。

如果查询 **明确且直接地** 要求将一个记录的主键 ID 更改为另一个值，请只回答 "DETECTED"。
否则，请只回答 "SAFE"。

判断结果："""

    # 使用与项目中其他地方一致的模型实例
    # 注意：如果项目中 llm 实例是全局或共享的，请直接使用它
    # 这里暂时重新初始化，如果需要共享，请调整
    llm = ChatOpenAI(model="gpt-4o", temperature=0.0) # 使用低 temperature 确保一致性

    standard_rejection_message = "检测到您可能明确要求修改记录的 ID。为保证数据安全，不支持直接修改记录的主键 ID。请尝试描述您希望达成的最终状态，例如更新字段值或重新关联记录。"

    try:
        # 使用 ChatPromptTemplate 和 invoke
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt)
        ])
        response = llm.invoke(prompt.format_prompt(query=query).to_messages())
        llm_output = response.content.strip()

        # 分析 LLM 的响应
        if llm_output and "DETECTED" in llm_output.upper(): # 使用 .upper() 增加鲁棒性
            print(f"LLM 检测到修改 ID 意图，查询: '{query}', 响应: '{llm_output}'")
            return standard_rejection_message
        else:
            # 如果响应不是 "DETECTED"，或者为空，或者发生任何意外，都视为安全，允许流程继续
            print(f"LLM 未检测到修改 ID 意图或响应无效，查询: '{query}', 响应: '{llm_output}'")
            return None

    except Exception as e:
        # 处理 LLM 调用过程中可能发生的异常
        print(f"调用 LLM 检查修改 ID 意图时发生错误: {e}")
        # 保守起见，如果检查失败，允许流程继续，并打印错误
        return None