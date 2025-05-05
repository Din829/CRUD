# langgraph_crud_app/services/llm/llm_delete_service.py

import json
from typing import List, Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from langgraph_crud_app.config import settings

# --- 新增：辅助函数：转义 JSON 字符串中的花括号 ---
def _escape_json_for_prompt(json_str: str) -> str:
    """
    转义 JSON 字符串中的字面量大括号，以防止与模板变量冲突。
    单大括号 { } 变双大括号 {{ }}。
    """
    if not json_str:
        return "{{}}" # 返回转义后的空对象表示
    # 确保只转义字面量大括号，不影响模板变量
    # 通过替换 { 为 {{ 和 } 为 }} 来实现
    escaped = json_str.replace("{", "{{").replace("}", "}}")
    return escaped

# Prompt 1: LLM 10 - 删除查询解析 (Adapted for LangChain)
# Note: Removed Dify specific variable syntax like {{#...#}}
GENERATE_DELETE_PREVIEW_SQL_PROMPT = """
你是一个数据库助手。根据用户输入和表结构，生成合法的 MySQL SELECT 语句，查询待删除的记录，仅用于预览或检查，不生成 DELETE 语句。

用户输入：
{user_query}
表结构：{schema_info}
表名：{table_names_str}
数据示例：{sample_data}

**核心要求：生成符合要求的完整SQL语句，确保语法正确且括号匹配，查询结果准确**

规则：
1. 动态识别目标表：
   - 从输入中提取表相关词（如"员工"-> "employee"，"菜品"-> "dish"，"分类"-> "category"）。
   - 若表名模糊（如"菜品分类表"），结合表结构和条件推断。
2. 解析条件：
   - 支持精确条件（如"id=5"）和自然语言条件（如"状态为禁用"）。
   - 复杂条件和过滤要求应准确转化为SQL语法，无需简化。
3. 生成SQL：
   - 格式：SELECT '[表名]' AS table_name, [主键] AS id, [字段1], [字段2], NULL AS extra1 FROM [表名] WHERE [条件]。
   - 可以使用任何必要的SQL语法（JOIN, 子查询, IN, EXISTS等）以满足查询需求。
   - 主键从表结构提取（"PRI"标记）。
4. 关联表：
   - 如查询涉及多个表的关联关系，使用UNION ALL连接多个SELECT语句。
   - 可以在每个SELECT中使用必要的子查询、JOIN等。

**极为重要**：
1. 生成的SQL必须是语法完整的，所有括号都必须正确匹配。
2. 不要强制简化复杂条件，准确性优先于简单性。
3. 确保生成的是完整的单条SQL语句，即使很长也要保持完整。
4. SQL语句应格式良好，使用适当的换行和缩进提高可读性。

示例：
- 输入："删除员工 id=5"
  输出：SELECT 'employee' AS table_name, id, name, username, NULL AS extra1 FROM employee WHERE id = '5';
- 输入："删除菜品分类表中状态为禁用的记录"
  输出：SELECT 'dish' AS table_name, id, name, description, NULL AS extra1 FROM dish WHERE status = '0';
- 输入："删除菜品 id=46 及其相关口味"
  输出：
  SELECT 'dish' AS table_name, id, name, description, NULL AS extra1 FROM dish WHERE id = '46'
  UNION ALL
  SELECT 'dish_flavor' AS table_name, id, name, value, NULL AS extra1 FROM dish_flavor WHERE dish_id = '46';
- 输入："删除所有仅拥有OpenAI令牌且创建了写作类别提示的用户及其令牌和提示"
  输出：
  SELECT 'users' AS table_name, id, username, email, NULL AS extra1 
  FROM users 
  WHERE id IN (
    SELECT u.id 
    FROM users u
    JOIN api_tokens t ON u.id = t.user_id
    LEFT JOIN api_tokens t2 ON u.id = t2.user_id AND t2.provider <> 'OpenAI'
    WHERE t.provider = 'OpenAI' AND t2.id IS NULL
    AND EXISTS (SELECT 1 FROM prompts p WHERE p.user_id = u.id AND p.category = 'writing')
  )
  UNION ALL
  SELECT 'api_tokens' AS table_name, id, user_id, provider, NULL AS extra1 
  FROM api_tokens 
  WHERE user_id IN (
    SELECT u.id 
    FROM users u
    JOIN api_tokens t ON u.id = t.user_id
    LEFT JOIN api_tokens t2 ON u.id = t2.user_id AND t2.provider <> 'OpenAI'
    WHERE t.provider = 'OpenAI' AND t2.id IS NULL
    AND EXISTS (SELECT 1 FROM prompts p WHERE p.user_id = u.id AND p.category = 'writing')
  )
  UNION ALL
  SELECT 'prompts' AS table_name, id, user_id, title, NULL AS extra1 
  FROM prompts 
  WHERE user_id IN (
    SELECT u.id 
    FROM users u
    JOIN api_tokens t ON u.id = t.user_id
    LEFT JOIN api_tokens t2 ON u.id = t2.user_id AND t2.provider <> 'OpenAI'
    WHERE t.provider = 'OpenAI' AND t2.id IS NULL
    AND EXISTS (SELECT 1 FROM prompts p WHERE p.user_id = u.id AND p.category = 'writing')
  );
"""

# Prompt for Formatting Delete Preview (Based on Dify LLM 11 Goal)
FORMAT_DELETE_PREVIEW_PROMPT = """
System: 你是一个信息整理助手。将以下 JSON 格式的查询结果整理成用户易于阅读的文本列表，说明将要删除哪些记录。

Input JSON Data (查询结果):
{delete_show_json}

Database Schema (参考):
{schema_info}

规则:
1.  **检查空数据**: 如果输入 JSON 数据为空列表 (`[]`) 或无效，直接输出 "未找到需要删除的记录。"
2.  **分组**: 严格按照每条记录中的 "table_name" 字段进行分组。
3.  **字段展示**: 对于每条记录，清晰地列出其关键字段和对应值。优先显示主键（通常是 "id" 字段）和其他能代表记录身份的字段（如 "name", "username" 等）。不需要展示所有字段。
4.  **格式**:
    *   每个表的数据以 `表名 [table_name]:` 开头。
    *   每条记录的关键字段信息另起一行，用 ` - 字段名: 值` 的格式。
    *   不同记录之间用 `----` 分隔。
    *   不同表的数据组之间用一个空行分隔。
5.  **简洁清晰**: 使用自然语言，避免技术术语。
6.  **纯文本**: 输出纯文本，不要包含 Markdown 或代码块标记。

示例输出 (假设输入 JSON 包含员工和日志记录):
表名 emp:
 - id: 54
 - name: 王五
 - username: wangwu
----
 - id: 55
 - name: 孙七
 - username: sunqi

表名 operate_log:
 - id: 1
 - info: 登录操作

现在，请根据提供的 JSON 数据和 Schema 整理预览文本。
"""

# Prompt 2: LLM 9 - 批量删除解析 (Adapted for LangChain)
# 模仿 llm_composite_service.py 的风格重写
PARSE_DELETE_IDS_PROMPT = """
System: 你是一个数据提取助手。根据以下查询返回的数据（JSON格式）和数据库信息，提取每个表中要删除记录的主键值列表。

查询返回的数据 (JSON 格式):
{delete_show_json}

表结构 (参考):
{schema_info}

表名列表 (参考):
{table_names_str}

规则：
1.  **输出格式**: 严格输出单一的 JSON 对象 `{{...}}`。此对象必须包含一个键 `"result"`，其值是一个字典，其中键是表名 (字符串)，值是对应表的主键值列表 (字符串列表，即使主键是数字也输出为字符串)。确保 JSON 格式有效，键和字符串值使用双引号。**输出纯 JSON 对象，不要包含任何其他文本或 Markdown 标记。**
2.  **解析输入**: 输入的 `delete_show_json` 是一个 JSON 数组，每个对象代表一条待删除的记录，包含 `table_name` 和其他字段。
3.  **分组**: 严格按照每个记录的 `table_name` 字段进行分组。
4.  **提取主键**: 对于每个表，根据 `schema_info` 确定其主键字段名（查找 "key": "PRI" 的字段）。然后从该表对应的所有记录中提取此主键字段的值。
5.  **空/无效输入**: 如果输入的 `delete_show_json` 为空数组 `[]` 或无法解析，或者解析后没有任何有效记录，返回空结果对象 `{{"result": {{}}}}`。

示例：
- 输入数据 (delete_show_json 的值为): `[{"table_name": "emp", "id": "54", "name": "赵六"}, {"table_name": "emp_expr", "id": "7", "emp_id": "54"}]`
  输出:
  ```json
  {{
    "result": {{
      "emp": ["54"],
      "emp_expr": ["7"]
    }}
  }}
  ```
- 输入数据 (delete_show_json 的值为): `[{"table_name": "operate_log", "id": "1", "class_name": "DeptController"}, {"table_name": "operate_log", "id": "39", "class_name": "StudentController"}]`
  输出:
  ```json
  {{
    "result": {{
      "operate_log": ["1", "39"]
    }}
  }}
  ```
- 输入数据 (delete_show_json 的值为): `[]`
  输出:
  ```json
  {{
    "result": {{}}
  }}
  ```
"""

def generate_delete_preview_sql(user_query: str, schema_info: str, table_names: List[str], sample_data: str) -> str:
    """
    使用 LLM 根据用户输入生成用于预览待删除记录的 SELECT SQL。
    """
    print("--- LLM 服务: 生成删除预览 SQL ---")
    try:
        prompt = ChatPromptTemplate.from_template(GENERATE_DELETE_PREVIEW_SQL_PROMPT)
        # 使用较低温度保证 SQL 格式一致性
        llm = ChatOpenAI(model=settings.OPENAI_MODEL_NAME, temperature=0.1)
        chain = prompt | llm

        table_names_str = ", ".join(table_names) if table_names else "无"

        response = chain.invoke({
            "user_query": user_query,
            "schema_info": schema_info,
            "table_names_str": table_names_str,
            "sample_data": sample_data
        })

        sql_output = response.content.strip()
        print(f"--- LLM 生成的 SQL (长度: {len(sql_output)}) ---")
        print(f"--- SQL前100个字符: {sql_output[:100]}... ---")
        print(f"--- SQL最后100个字符: ...{sql_output[-100:]} ---")

        # 基本检查：是否返回了提示信息而不是 SQL
        if sql_output.startswith("请提供有效") or sql_output == "":
             print("--- LLM 返回提示信息，非有效 SQL ---")
             # 将提示信息返回给 action node 处理
             return sql_output
        # 确保SQL是SELECT语句
        elif not sql_output.upper().strip().startswith("SELECT"):
             print("--- LLM 输出似乎不是有效的 SELECT 语句 ---")
             # 同样返回给 action node 处理
             return f"错误：LLM 未生成有效的 SELECT 语句。返回内容：{sql_output[:100]}..."

        # SQL语法检查和修复
        sql_output = sql_output.strip()
        
        # 检查是否包含UNION ALL，确保每部分都是完整的
        if " UNION ALL " in sql_output.upper():
            parts = sql_output.upper().split(" UNION ALL ")
            for i, part in enumerate(parts):
                if not part.strip().startswith("SELECT"):
                    print(f"--- 警告：UNION ALL第{i+1}部分不是有效的SELECT语句 ---")
                    # 可能需要二次生成修复
            print(f"--- 检测到包含{len(parts)}个UNION ALL连接的查询 ---")

        # 检查SQL是否以分号结尾，如果没有则添加
        if not sql_output.endswith(';'):
            sql_output = sql_output + ';'
            print("--- 为SQL添加了分号 ---")
        
        # 安全性检查：确保SQL中不包含多条语句（防止SQL注入）
        if sql_output.count(';') > 1:
            print("--- 警告：SQL包含多个语句，可能存在安全风险 ---")
            # 只保留第一条语句
            sql_output = sql_output.split(';')[0] + ';'
            print(f"--- 清理后的SQL: {sql_output[:100]}... ---")

        return sql_output

    except Exception as e:
        print(f"--- 调用 generate_delete_preview_sql 时出错: {e} ---")
        # 向上抛出异常，由 action node 捕获并存入 delete_error_message
        raise ValueError(f"生成删除预览 SQL 失败: {e}") from e


def format_delete_preview(delete_show_json: str, schema_info: str) -> str:
    """
    使用 LLM 将查询到的待删除记录 (JSON 字符串) 格式化为用户友好的文本。
    """
    print("--- LLM 服务: 格式化删除预览 ---")
    try:
        # 预检查输入是否为空列表的 JSON 字符串
        if delete_show_json.strip() == '[]':
            return "未找到需要删除的记录。"

        prompt = ChatPromptTemplate.from_template(FORMAT_DELETE_PREVIEW_PROMPT)
        llm = ChatOpenAI(model=settings.OPENAI_MODEL_NAME, temperature=0.2)
        chain = prompt | llm

        response = chain.invoke({
            "delete_show_json": delete_show_json,
            "schema_info": schema_info
        })
        preview_text = response.content.strip()
        print(f"--- LLM 格式化预览结果: ---\n{preview_text}\n---------------------")
        return preview_text

    except Exception as e:
        print(f"--- 调用 format_delete_preview 时出错: {e} ---")
        # 提供回退预览
        try:
            # 尝试解析原始 JSON 以提供一些信息
            data = json.loads(delete_show_json)
            fallback_preview = f"无法生成格式化预览 ({e})。将尝试删除以下记录 (原始 JSON)：\n{json.dumps(data, indent=2, ensure_ascii=False)}"
        except Exception:
            fallback_preview = f"无法生成格式化预览 ({e}) 且无法解析原始 JSON 数据。"
        return fallback_preview

def parse_delete_ids(delete_show_json: str, schema_info: str, table_names: List[str]) -> str:
    """
    使用 LLM 从预览数据 (JSON 字符串) 中解析出待删除记录的 ID，按表分组。
    返回包含 {{"result": {{"table": ["id1", ...], ...}}}} 的 JSON 字符串。
    """
    print("--- LLM 服务: 解析待删除 ID ---")
    if delete_show_json.strip() == '[]':
        print("--- 输入 delete_show_json 为空列表，返回空结果 JSON ---")
        return '{{"result": {{}}}}'
    try:
        # --- 恢复：使用默认的模板创建方式，移除 format 和变量检查 ---
        prompt = ChatPromptTemplate.from_template(PARSE_DELETE_IDS_PROMPT)

        llm = ChatOpenAI(model=settings.OPENAI_MODEL_NAME, temperature=0.1)
        chain = prompt | llm

        table_names_str = ", ".join(table_names) if table_names else "无"

        # 保持原始调用
        response = chain.invoke({
            "delete_show_json": delete_show_json,
            "schema_info": schema_info,
            "table_names_str": table_names_str
        })
        llm_output = response.content.strip()
        print(f"--- LLM 解析 ID 原始输出: ---\n{llm_output}\n------------------------")

        # 清理可能的 Markdown 代码块标记
        if llm_output.startswith("```json"):
            llm_output = llm_output[7:]
        if llm_output.endswith("```"):
            llm_output = llm_output[:-3]
        llm_output = llm_output.strip() # 清理后再次 strip

        # 基本验证 LLM 输出是否为有效 JSON 且符合基本结构
        try:
            parsed_output = json.loads(llm_output)
            if "result" not in parsed_output or not isinstance(parsed_output["result"], dict):
                raise ValueError("LLM 输出缺少 'result' 键或其值不是字典")
            for table, ids in parsed_output["result"].items():
                 if not isinstance(ids, list):
                      raise ValueError(f"表 '{{table}}' 的值不是列表")
            # 返回清理后的 JSON 字符串
            return llm_output
        except (json.JSONDecodeError, ValueError) as e:
            print(f"--- LLM 输出的 JSON 格式无效或结构错误: {{e}} ---")
            # 向上抛出异常，让 action node 处理
            raise ValueError(f"LLM未能按要求格式生成待删除 ID 的 JSON: {{e}}") from e

    except Exception as e:
        print(f"--- 调用 parse_delete_ids 时出错: {{e}} ---")
        if "in format string" in str(e) or "missing variables" in str(e):
             print("--- 检测到 Prompt 模板格式错误。请再次检查 PARSE_DELETE_IDS_PROMPT 中的大括号转义。 ---")
        raise ValueError(f"解析待删除 ID 失败: {{e}}") from e 

def parse_delete_ids_direct(delete_show_json: str, schema_info: str, table_names: List[str]) -> str:
    """
    直接解析待删除记录的JSON字符串，提取ID，按表分组。
    不依赖LLM模板，避免解析问题。
    
    Args:
        delete_show_json: JSON字符串，包含待删除记录信息
        schema_info: 数据库Schema信息
        table_names: 表名列表
        
    Returns:
        JSON字符串，格式为 {"result": {"table_name": ["id1", "id2"], ...}}
    """
    print("--- 服务: 直接解析待删除ID ---")
    
    # 处理空输入
    if not delete_show_json or delete_show_json.strip() == '[]' or delete_show_json.strip() == '{}':
        print("--- 输入delete_show_json为空或为空列表/空对象，返回空结果JSON ---")
        return '{"result": {}}'
    
    try:
        # 解析输入JSON
        records = json.loads(delete_show_json)
        
        # 检查解析后的结果是否为空列表
        if not records or (isinstance(records, list) and len(records) == 0):
            print("--- 解析后的数据为空，返回空结果JSON ---")
            return '{"result": {}}'
            
        result = {}
        
        # 按表名分组，提取ID
        for record in records:
            table_name = record.get("table_name")
            if not table_name:
                print(f"--- 警告: 记录缺少table_name字段: {record} ---")
                continue
                
            # 查找ID字段（通常是"id"）
            id_value = record.get("id")
            if not id_value:
                print(f"--- 警告: 记录缺少id字段: {record} ---")
                continue
                
            # 添加到结果
            if table_name not in result:
                result[table_name] = []
            if id_value not in result[table_name]:
                result[table_name].append(id_value)
        
        # 检查结果是否为空
        if not result:
            print("--- 未能从记录中提取任何有效ID，返回空结果JSON ---")
            return '{"result": {}}'
            
        print(f"--- 成功提取待删除ID: {result} ---")
        # 返回符合格式的JSON
        return json.dumps({"result": result}, ensure_ascii=False)
    except json.JSONDecodeError as e:
        print(f"--- 解析JSON失败: {e} ---")
        raise ValueError(f"解析待删除记录JSON失败: {e}")
    except Exception as e:
        print(f"--- 解析待删除ID时出错: {e} ---")
        raise ValueError(f"解析待删除ID失败: {e}") 