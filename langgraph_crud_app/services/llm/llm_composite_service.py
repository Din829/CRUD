"""
封装处理复合操作请求（如同时修改和新增）的 LLM 调用逻辑。
"""

import json
from typing import Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import re

from langgraph_crud_app.config import settings

# === 核心函数 ===

def parse_combined_request(
    user_query: str,
    schema_info: str,
    table_names: List[str],
    sample_data: str
) -> List[Dict[str, Any]]:
    """
    使用 LLM 解析用户的复合请求（可能包含修改、新增、删除等），
    并生成一个结构化的操作列表。
    (已更新 Prompt 以处理隐式查找和改进依赖处理)

    Args:
        user_query: 用户的原始自然语言请求。
        schema_info: 数据库 Schema 的 JSON 字符串。
        table_names: 数据库中的表名列表。
        sample_data: 数据示例的 JSON 字符串。

    Returns:
        一个操作字典的列表，每个字典描述一个数据库操作。
        如果解析失败或无有效操作，则返回空列表。

    Raises:
        ValueError: 如果 LLM 调用失败或返回格式严重错误。
    """
    print(f"--- LLM 服务: 解析复合请求 (增强 Prompt): {user_query[:100]}... ---")

    # --- Prompt 设计 (对齐单一流程, 处理复合操作, 增强查找和依赖) ---
    prompt_template = """
你是一个强大的数据库操作规划器。你的任务是仔细分析用户的自然语言请求，该请求可能包含多个步骤，涉及对数据库的修改(UPDATE)、新增(INSERT)或删除(DELETE)操作。你需要将用户的请求分解为一系列按顺序执行的原子数据库操作，并以 JSON 列表的格式输出。

可用信息:
- 用户请求: {query}
- 数据库 Schema (JSON): {schema}
- 表名列表: {tables}
- 数据示例 (JSON): {sample}

**核心规则:**

1.  **输出格式**: 严格输出 JSON 列表 `[...]`。列表中的每个元素是一个代表单一数据库操作的 JSON 对象 `{{...}}`。输出纯 JSON 列表，不要包含任何其他文本或 Markdown 标记。如果无法解析或请求无效，返回空列表 `[]`。
2.  **操作对象结构**: 每个操作对象必须包含 `"operation"` 键 (`"insert"`, `"update"`, `"delete"`) 和 `"table_name"` 键。
3.  **字段和表名**: 严格使用提供的 Schema 中的表名和字段名。
4.  **顺序**: 列表中的操作顺序应尽可能反映逻辑依赖关系。

**特殊值处理:**

*   **数据库查询占位符 `{{{{db(...)}}}}`**: 如果操作（insert/update/delete）的某个值需要基于名称或描述从**其他表**查找获得（例如 "用户 'bob' 的 ID"，"分类为 '甜品' 的 ID"），**必须**在该操作的 `values` 或 `where` 子句中使用 `{{{{db(SELECT id FROM <相关表> WHERE <相关字段> = '值')}}}}` 占位符。你需要根据 Schema 和用户意图构造合适的 SQL 查询。**不要**为这种查找生成单独的操作步骤。
*   **随机值占位符 `{{{{random(...)}}}}`**: 如果用户要求生成随机值 (例如 "随机密码", "生成UUID"), **必须**根据字段类型和常见模式生成 `{{{{random(string)}}}}`, `{{{{random(integer)}}}}`, `{{{{random(uuid)}}}}` 等占位符。 **不要自己生成实际的随机值**。
*   **当前时间**: 如果用户要求使用当前时间，在 `values` 或 `set` 中使用字符串 `"now()"`。
*   **SQL 表达式 (仅限 UPDATE)**: 如果 `update` 操作的 `set` 子句需要引用**被更新行本身**的其他字段进行计算（如 `count + 1`），直接在 `set` 的值中写入 SQL 表达式字符串，例如 `{{"count": "count + 1"}}` 或 `{{"email": "CONCAT(username, '@my.com')"}}`。

**操作类型细节:**

*   **`insert`**:
    *   必须包含 `"values"` 字典。
    *   **主键**: 参考 Schema，如果是自增主键 (通常 `extra` 包含 `auto_increment`)，**不要**在 `values` 中包含主键字段。如果是非自增主键，必须提供其值（可能是一个 `{{db(...)}}` 占位符）。
    *   **依赖返回**: 如果后续操作需要此插入记录的 ID 或其他字段值，添加 `"return_affected": ["字段名1", ...]` (通常是主键字段名，如 `"id"`)。

*   **`update`**:
    *   必须包含 `"where"` 字典（不能为空，其值可能是字面量或 `{{db(...)}}` 或 `{{previous_result[...]}}`）和 `"set"` 字典（不能为空）。
    *   **依赖返回**: 如果后续操作需要此更新记录的某个字段值，添加 `"return_affected": ["字段名1", ...]`。

*   **`delete`**:
    *   必须包含 `"where"` 字典（不能为空，其值可能是字面量或 `{{db(...)}}` 或 `{{previous_result[...]}}`）。

**依赖关系处理 (`depends_on_index` 和 `{{previous_result...}}`)**:

*   如果一个操作（操作 B，索引 `M`）需要用到列表中**先前**某个操作（操作 A，索引 `N`，且 **N < M**）返回的值（通过 `"return_affected"` 指定），则：
    1.  在操作 B 中添加 `"depends_on_index": N`。 **必须确保 N 小于 M**。
    2.  在操作 B 的 `values`, `set`, 或 `where` 子句中，使用占位符 `"{{{{previous_result[N].字段名}}}}"` 来引用操作 A 返回的值。例如：`{{"user_id": "{{{{previous_result[0].id}}}}"}}`。

**示例:**

*   请求："添加用户'bob'，邮箱'bob@a.com'；然后更新该用户的邮箱为'bob@b.com'"
    ```json
    [
      {{{{
        "operation": "insert",
        "table_name": "users",
        "values": {{"username": "bob", "email": "bob@a.com", "created_at": "now()", "updated_at": "now()"}},
        "return_affected": ["id"]
      }}}},
      {{{{
        "operation": "update",
        "table_name": "users",
        "where": {{"id": "{{{{previous_result[0].id}}}}"}},
        "set": {{"email": "bob@b.com", "updated_at": "now()"}},
        "depends_on_index": 0
      }}}}
    ]
    ```
*   请求："为用户'alice'创建一个提示，标题是'周报'，内容是'本周工作总结'，类别是'work'，然后将类别改为'report'。" (假设 Schema 中 users 表有 id, username; prompts 表有 id, user_id, title, content, category)
    ```json
    [
      {{{{
        "operation": "insert",
        "table_name": "prompts",
        "values": {{
          "user_id": "{{{{db(SELECT id FROM users WHERE username = 'alice')}}}}",
          "title": "周报",
          "content": "本周工作总结",
          "category": "work",
          "created_at": "now()",
          "updated_at": "now()"
        }},
        "return_affected": ["id"]
      }}}},
      {{{{
        "operation": "update",
        "table_name": "prompts",
        "where": {{
          "id": "{{{{previous_result[0].id}}}}"
        }},
        "set": {{
          "category": "report",
          "updated_at": "now()"
        }},
        "depends_on_index": 0
      }}}}
    ]
    ```
*   请求："删除用户 ID 为 15 的所有 prompts 记录，然后为 ID 为 15 的用户新增一个 api_token，provider 是 'test'，token_value 是 'abc'。" (假设 prompts.user_id 是外键)
    ```json
    [
      {{{{
        "operation": "delete",
        "table_name": "prompts",
        "where": {{"user_id": 15}}
      }}}},
      {{{{
        "operation": "insert",
        "table_name": "api_tokens",
        "values": {{"user_id": 15, "provider": "test", "token_value": "abc", "created_at": "now()", "updated_at": "now()"}}
      }}}}
    ]
    ```

请根据上述规则，将以下用户请求转换为操作列表:
用户请求: {query}
"""
    # --- Prompt 设计结束 ---

    try:
        prompt = ChatPromptTemplate.from_template(prompt_template)
        llm = ChatOpenAI(model="gpt-4o", temperature=0.0) # 保持低温度以获得确定性输出
        chain = prompt | llm

        response = chain.invoke({
            "query": user_query,
            "schema": schema_info,
            "tables": table_names,
            "sample": sample_data
        })

        llm_output = response.content.strip()
        print(f"--- LLM 解析复合请求原始输出:\n{llm_output}\n---")

        # 清理 Markdown
        if llm_output.startswith("```json"):
            llm_output = llm_output[7:]
        if llm_output.endswith("```"):
            llm_output = llm_output[:-3]
        llm_output = llm_output.strip()

        # 移除行内注释
        import re
        # 修复：确保移除注释后不会破坏 JSON 结构（例如移除逗号）
        # 更安全的做法是逐行处理，只移除行尾的注释
        lines = llm_output.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_line = re.sub(r"//.*$", "", line) # 只移除行尾的 // 注释
            # 检查移除注释后是否只剩下空白和逗号，如果是，则保留逗号以维持 JSON 结构
            stripped_line = cleaned_line.strip()
            if stripped_line == ',' or stripped_line: # 保留逗号行或非空行
                cleaned_lines.append(cleaned_line)
            elif line.strip().endswith(','): # 如果原行以逗号结尾，但移除注释后变空，补回逗号
                cleaned_lines.append(',')

        llm_output = "\n".join(cleaned_lines)
        # 在解析前再次 strip 以移除可能的前导/尾随空白
        llm_output = llm_output.strip()

        print(f"--- LLM 解析复合请求 (清理后):\n{llm_output}\n---")


        # 解析 JSON 列表
        # 添加额外的检查，防止解析空的或无效的字符串
        if not llm_output or llm_output == "[]":
            print("错误: 清理后的 LLM 输出为空或无效，返回空列表。")
            return []

        parsed_plan = json.loads(llm_output)
        if not isinstance(parsed_plan, list):
            print("错误: LLM 输出不是有效的 JSON 列表。")
            return []

        # === 新增：基本逻辑校验 ===
        for i, op in enumerate(parsed_plan):
            depends_on = op.get("depends_on_index")
            if depends_on is not None:
                if not isinstance(depends_on, int) or depends_on < 0 or depends_on >= i:
                    print(f"错误: 解析后的计划包含无效依赖 (操作 {i} 依赖于 {depends_on})。")
                    # 可以选择返回空列表或抛出异常
                    return [] # 返回空列表表示计划无效
        # === 校验结束 ===

        print(f"--- LLM 解析复合请求成功，生成操作计划: {parsed_plan} ---")
        return parsed_plan

    except json.JSONDecodeError as e:
        print(f"错误: 解析 LLM 输出的 JSON 列表失败: {e}\n清理后输出: {llm_output}")
        return []
    except Exception as e:
        print(f"错误: 调用 LLM 解析复合请求时发生错误: {e}")
        raise ValueError(f"LLM call for combined request failed: {e}") from e

def format_combined_preview(
    user_query: str,
    combined_operation_plan: List[Dict[str, Any]]
) -> str:
    """
    使用 LLM 将结构化的复合操作计划格式化为用户友好的预览文本。

    Args:
        user_query: 用户的原始查询（供 LLM 参考）。
        combined_operation_plan: 由 parse_combined_request 生成的操作列表。

    Returns:
        用户友好的复合操作文本预览。
    """
    print(f"--- 调用 LLM 格式化复合操作预览 ---")

    # --- Prompt 设计 --- 
    # 目标：清晰地向用户展示将要执行的所有步骤
    prompt_template = """
    你是一个清晰简洁的沟通助手。用户的请求已被解析为一系列数据库操作步骤。请将这些步骤用自然语言清晰地展示给用户，以便用户确认。

    参考信息:
    - 用户原始请求: {query}
    - 将要执行的操作计划 (JSON 列表): {plan}

    预览要求:
    1.  **概述**: 首先简单说明将要执行一个包含多个步骤的操作。
    2.  **分步**: 使用有序列表（1., 2., ...）清晰列出每个操作。
    3.  **描述**: 对每个操作，用自然语言描述：
        - 操作类型 (例如: 更新、新增、删除)。
        - 目标表 (例如: `users` 表)。
        - 关键信息：
            - 更新 (Update): 指明更新条件 (例如: ID=5 的记录) 和要修改的字段及新值。
            - 新增 (Insert): 指明要新增的主要字段和值。
            - 删除 (Delete): 指明删除条件 (例如: ID=10 的记录)。
    4.  **简洁**: 省略不必要的数据库技术细节（如精确的 where 子句），除非关键。
    5.  **依赖**: 不需要明确说明操作间的依赖关系。
    6.  **结尾**: 最后加上标准的确认请求语，例如"请确认是否执行这些操作？"

    示例:
    操作计划: `[{{"operation": "update", "table_name": "users", "where": {{"id": 5}}, "set": {{"email": "new@example.com"}}}}, {{"operation": "insert", "table_name": "user_tags", "values": {{"user_id": 5, "tag_name": "vip"}}}}]`
    示例预览:
    "好的，我将为您执行以下包含 2 个步骤的操作：
    1. 更新 `users` 表中 ID 为 5 的记录，将 email 设置为 new@example.com。
    2. 在 `user_tags` 表中新增一条记录，设置 user_id 为 5，tag_name 为 'vip'。
    请确认是否执行这些操作？"

    现在，请根据以下信息生成预览文本:
    用户原始请求: {query}
    操作计划:
    {plan}
    """
    # --- Prompt 设计结束 ---

    try:
        prompt = ChatPromptTemplate.from_template(prompt_template)
        llm = ChatOpenAI(model=settings.OPENAI_MODEL_NAME, temperature=0.2)
        chain = prompt | llm

        # 将操作计划序列化为 JSON 字符串
        plan_json = json.dumps(combined_operation_plan, ensure_ascii=False, indent=2)

        response = chain.invoke({
            "query": user_query,
            "plan": plan_json
        })
        preview_text = response.content.strip()
        print(f"--- LLM 格式化复合预览结果: {preview_text} ---")
        return preview_text

    except Exception as e:
        print(f"--- LLM 格式化复合预览出错: {e} ---")
        # 返回一个通用的错误或默认预览
        plan_str_fallback = json.dumps(combined_operation_plan, ensure_ascii=False, indent=2)
        return f"无法生成清晰的预览。将尝试执行以下操作计划，请谨慎确认：\n{plan_str_fallback}" 