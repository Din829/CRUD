import json
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from langgraph_crud_app.config import settings

# TODO: 根据 Dify 定义 Prompt (节点 1742607431930 和 1744932102704)
PARSE_ADD_REQUEST_PROMPT = """
# 占位符: 根据 Dify 节点 1742607431930 定义 Prompt
System: 你是一个数据输入助手...
User: Input: {{query}}, Schema: {{schema}}, Tables: {{tables}}, Sample: {{sample}}
"""

# --- 辅助函数：转义 JSON 字符串中的花括号 ---
# 参考 llm_modify_service.py
# def _escape_json_for_prompt(json_str: str) -> str:
#     """
#     转义 JSON 字符串中的大括号，以防止与 f-string 或模板变量冲突。
#     """
#     if not json_str:
#         return "{{}}" # 返回转义后的空对象
#     # 将字面量的 { 和 } 替换为 {{ 和 }}
#     escaped = json_str.replace("{", "{{").replace("}", "}}")
#     return escaped

# 基于 Dify 节点 1744932102704 的目标定义 Prompt
FORMAT_ADD_PREVIEW_PROMPT = """
System: 你是一个数据库助手。你的任务是根据提供的、已经处理过占位符的结构化数据，生成一段清晰、简洁、用户友好的文本预览，告知用户将要执行的新增操作。

Input:
- 用户原始请求 (参考): {query}
- 数据库 Schema (参考): {schema}
- 涉及的表 (参考): {table_names}
- 将要插入的结构化记录 (JSON 格式): {processed_records}

规则:
1.  **重点**: 准确地反映 `processed_records` 中的数据。
2.  **清晰**: 使用自然语言描述将要向哪个表新增哪些数据。
3.  **简洁**: 避免技术术语，除非必要。
4.  **格式**:
    - 如果有多条记录或涉及多个表，请使用列表或分点清晰展示。
    - 对于每条记录，列出关键的字段和值。
5.  **语气**: 确认性、信息性的语气。

示例输出 (假设 processed_records 包含一条用户信息):
"好的，我将为您在 `users` 表中新增一条记录，包含以下信息：
- username: 奥里给
- email: abc123xyz@example.com
- password: (已生成)
请确认是否执行？"

示例输出 (假设 processed_records 包含多条记录和多个表):
"好的，我将为您执行以下新增操作：
1.  在 `employees` 表新增一条记录：
    - name: 张三
    - department_id: 1
2.  在 `operate_log` 表新增一条记录：
    - info: 新增员工张三
请确认是否执行？"

现在，请根据以下信息生成预览文本：
用户原始请求: {query}
数据库 Schema: {schema}
涉及的表: {table_names}
将要插入的结构化记录:
{processed_records}
"""


def parse_add_request(user_query: str, schema_info: str, sample_data: str) -> str:
    """
    使用 LLM 解析用户的新增数据请求。
    回归使用 ChatPromptTemplate.from_template，并仔细转义所有字面花括号。
    """
    print(f"--- LLM 服务: 解析新增请求 (ChatPromptTemplate & Dify Prompt): {user_query} ---")

    # 定义模板字符串，变量用单括号，字面量用双括号
    dify_prompt_template_escaped = """
你是一个数据输入助手。根据用户提供的自然语言内容 和表结构 ，生成一个结构化的 JSON 字符串
请遵循以下规则：
- 输入内容: {query}
- 表名: [用户可能提到的表，参考下面的表结构]
- 表结构: {schema}
- 数据示例: {sample}

1. **输入解析**:
   - 支持键值对（如 "字段名: 值"）或自然语言（如"员工姓名是张三"）。
   - 支持多表（如"新增员工 username=张三 并记录日志"）和多条记录（如"新增两条员工：username=张三；username=李四"）。
   - 字段名需与表结构一致，支持英文/中文，值保留完整（如"草鱼2斤"不拆分）。
   - **特殊占位符生成**: 根据用户意图生成以下占位符，**不要自己计算或生成随机值**:
     - **数据库查询占位符**: 如果用户输入的值需要通过查询其他表获得 (例如 "分类为甜品")，请生成 `{{{{db(SELECT id FROM category WHERE name = '甜品')}}}}` 这样的占位符。你需要根据表结构和用户意图自行构造合适的 SQL 查询语句。
     - **随机值占位符**: 如果用户要求随机值 (例如 "随机生成邮箱", "密码随机"), 请根据字段类型和常见模式生成 `{{{{random(string)}}}}`, `{{{{random(integer)}}}}`, `{{{{random(uuid)}}}}` 或其他合理类型。
     - **新记录 ID 引用**: 如果一个操作依赖于同一次新增操作中另一条记录的主键 (例如新增订单及其详情)，请使用 `{{{{new(表名.主键字段名)}}}}` (例如 `{{{{new(orders.id)}}}}`)。
   - **主键处理**: 识别表的主键（标记为 "PRI" 或 '(主键)'）。如果用户未提供主键值，并且它不是自增的，你需要考虑是否应该生成一个随机占位符 `{{{{random(uuid)}}}}` 或 `{{{{random(integer)}}}}`，具体取决于字段类型。如果主键是自增的，则省略该字段。

2. **字段校验**: 字段名需在提供的表结构中，否则忽略该字段或返回错误提示。

3. **日期处理**: 识别日期/时间相关的输入，如果用户要求当前时间，使用 `now()`，否则尽量保持用户输入格式或转换为 `YYYY-MM-DD HH:MM:SS`。

4. **输出格式**: 严格输出 JSON，格式为 `{{{{"result": {{ "表名1": [{{{{"字段1": "值1", ...}}}}, ...], "表名2": [...]}}}}}}}}`，用双引号包裹键和字符串值。将整个 JSON 包裹在 `<output>json ... </output>` 标签中。

5. **空/无效输入**: 如果无法解析出任何有效数据，返回 `<output>json{{{{"result": {{}}}}}}</output>`。

示例：
- 输入："新增员工 username=张三, name=张三, dept_id=1 并记录操作日志 info=新增员工张三"
  <output>
json
{{{{"result": {{ "emp": [{{{{"username": "张三", "name": "张三", "dept_id": "1"}}}}], "operate_log": [{{{{"info": "新增员工张三", "create_time": "now()"}}}}]}}}}}}
</output>

- 输入："新增一个菜品，名称 芒果布丁，分类为甜品，价格 15.00"
  <output>
json
{{{{"result": {{ "dish": [{{{{"name": "芒果布丁", "category_id": "{{{{db(SELECT id FROM category WHERE name = '甜品')}}}}", "price": "15.00"}}}}]}}}}}}
</output>

- 输入："新增一个用户，用户名 奥里给，邮箱随机，密码随机"
  <output>
json
{{{{"result": {{ "users": [{{{{"username": "奥里给", "email": "{{{{random(string)}}}}@example.com", "password": "{{{{random(string)}}}}"}}}}]}}}}}}
</output>

- 输入："创建订单，关联用户 ID 5，然后添加订单项，商品ID 10，数量 2"
  <output>
json
{{{{"result": {{ "orders": [{{{{"user_id": "5", "order_time": "now()"}}}}], "order_items": [{{{{"order_id": "{{{{new(orders.id)}}}}", "product_id": "10", "quantity": 2}}}}]}}}}}}
</output>

现在，请根据以下信息处理用户输入:
用户输入: {query}
表结构:
{schema}
数据示例 (供参考):
{sample}
"""

    try:
        # 使用 ChatPromptTemplate 处理模板
        prompt = ChatPromptTemplate.from_template(dify_prompt_template_escaped)
        llm = ChatOpenAI(model=settings.OPENAI_MODEL_NAME, temperature=0.1)
        chain = prompt | llm

        print("--- Calling LLM for add request parsing (using ChatPromptTemplate) ---")
        # 传递未转义的原始输入给 invoke
        response = chain.invoke({
            "query": user_query,
            "schema": schema_info,
            "sample": sample_data
        })

        llm_output = response.content
        print(f"--- LLM Raw Output:\n{llm_output}\n---")

        # 基本验证：检查是否为空或只包含空的 result
        if not llm_output or '{"result": {}}' in llm_output.replace(" ", ""):
            print("--- LLM returned empty or no data result ---")
            # 这种情况通常意味着 LLM 无法从输入中提取数据，是正常流程，返回空结果的标记
            return "<output>json{\"result\": {}}</output>"

        # 检查是否包含必要的 <output> 标签
        if not llm_output.strip().startswith("<output>") or not llm_output.strip().endswith("</output>"):
            print("--- LLM output missing <output> tags. Attempting to wrap. ---")
            # 尝试包裹，但这可能不是完美的解决方案
            # 更好的做法是调整 Prompt 或在下一步骤处理
            # llm_output = f"<output>json{llm_output}</output>" # 暂时不自动包裹，让下游处理
            raise ValueError("LLM output missing required <output> tags.")

        return llm_output

    except Exception as e:
        print(f"--- Error during LLM call or processing: {e} ---")
        # 向上抛出异常，由调用者 (action node) 处理
        raise ValueError(f"LLM call failed: {e}") from e

def format_add_preview(query: str, schema: str, table_names: List[str], processed_records: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    调用 LLM 将处理过的新增数据格式化为用户友好的预览文本。

    Args:
        query: 用户的原始查询。
        schema: 数据库 schema 字符串。
        table_names: 表名列表。
        processed_records: 处理过的记录字典 (占位符处理后, 格式为 {"table_name": [{"field": "value"}, ...], ...})。

    Returns:
        用户友好的新增操作文本预览。
    """
    print(f"--- 调用 LLM 格式化新增预览 ---")
    try:
        llm = ChatOpenAI(model=settings.OPENAI_MODEL_NAME, temperature=0.2) # 使用较低温度确保一致性
        prompt = ChatPromptTemplate.from_template(FORMAT_ADD_PREVIEW_PROMPT)
        chain = prompt | llm

        # 将 processed_records 序列化为 JSON 字符串以便传递给 LLM
        records_json = json.dumps(processed_records, ensure_ascii=False, indent=2)

        response = chain.invoke({
            "query": query,
            "schema": schema,
            "table_names": ", ".join(table_names), # 将列表转换为逗号分隔的字符串
            "processed_records": records_json
        })
        preview_text = response.content
        print(f"--- LLM 格式化预览结果: {preview_text} ---")
        return preview_text
    except Exception as e:
        print(f"--- LLM 格式化预览出错: {e} ---")
        # 返回一个通用的错误或默认预览
        return f"""无法生成预览。将尝试新增以下数据：
{json.dumps(processed_records, ensure_ascii=False, indent=2)}""" 