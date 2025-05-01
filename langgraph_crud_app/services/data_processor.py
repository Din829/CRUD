# data_processor.py: 包含用于数据清理、转换和状态更新的工具函数。

from typing import List, Optional, Dict, Any, Set
import re # Import re for cleaning
import json # Import json
import random
import string
import uuid # Add uuid import for random UUID generation
# Import API client for placeholder resolution
from .api_client import execute_query 

def nl_string_to_list(names_str: str) -> List[str]:
    """
    将换行符分隔的字符串转换为字符串列表，并移除空行。

    对应 Dify code 节点 '1743382507830' 的逻辑。

    参数:
        names_str: 一个项目由换行符分隔的字符串。

    返回:
        一个非空字符串的列表。
    """
    if not names_str:
        return []
    # 按换行符分割，去除每个项目两端的空白，并过滤掉空字符串
    items = [name.strip() for name in names_str.split('\n') if name.strip()]
    # 新增：过滤掉可能的Markdown标记行
    items = [item for item in items if item != '```']
    return items

def clean_sql_string(sql: str) -> str:
    """
    清理 LLM 生成的 SQL 字符串，移除常见的多余字符。
    对应 Dify code 节点 '1742268810496' 和 '17432988044960' 的逻辑。

    Args:
        sql: 可能包含多余字符的 SQL 字符串。

    Returns:
        清理后的 SQL 字符串。
    """
    if not sql:
        return ""
    # 移除常见的 Markdown 代码块标记
    cleaned_sql = re.sub(r'^```sql\s*', '', sql, flags=re.IGNORECASE)
    cleaned_sql = re.sub(r'\s*```$', '', cleaned_sql)
    # 移除可能存在的前后空白符
    cleaned_sql = cleaned_sql.strip()
    # 将换行符替换为空格，并将多个空格合并为一个
    cleaned_sql = ' '.join(cleaned_sql.replace('\n', ' ').split())
    # 移除末尾可能的分号
    if cleaned_sql.endswith(';'):
        cleaned_sql = cleaned_sql[:-1].strip()
    return cleaned_sql 

def is_query_result_empty(result_str: Optional[str]) -> bool:
    """
    检查 API 查询结果的 JSON 字符串是否代表空列表。
    对应 Dify 条件分支 '1742269174054' 的逻辑。

    Args:
        result_str: API 返回的 JSON 字符串。

    Returns:
        如果结果是空列表 ('[]') 或无效/空字符串，则返回 True，否则 False。
    """
    if not result_str:
        return True
    try:
        # 尝试解析 JSON
        data = json.loads(result_str)
        # 检查是否是列表且为空
        if isinstance(data, list) and not data:
            return True
        # Dify 的 contains '[]' 逻辑比较宽松，这里也检查字符串本身
        if result_str.strip() == "[]":
            return True
    except json.JSONDecodeError:
        # 如果 JSON 无效，也视为空结果
        print(f"警告：无法解析查询结果 JSON 字符串 '{result_str}'，视为空结果。")
        return True
    return False 

# === 新增流程处理函数 ===

# 修改正则表达式以匹配 {{...}} 并捕获内部内容
PLACEHOLDER_PATTERN = re.compile(r'\{\{([^}]+)\}\}')

def clean_and_structure_llm_add_output(raw_output: str) -> List[Dict[str, Any]]:
    """
    清理 LLM 生成的新增请求输出，提取 JSON 内容，并结构化为记录列表。
    现在可以处理两种格式：
    1. Dify 风格: {"result": {"table_name": [{record_fields}, ...]}}
    2. 直接列表: [{ "table_name": ..., "fields": {record_fields} }, ...]

    Args:
        raw_output: LLM 返回的原始字符串，可能包含 <output> 标签和 Markdown。

    Returns:
        结构化的记录列表，统一格式为: `[{ "table_name": ..., "fields": ... }]`。
        如果解析失败或未找到有效内容，则返回空列表。
    """
    print(f"--- 清理和结构化 LLM 新增输出 ---")
    output_pattern = re.compile(r'<output>(.*?)</output>', re.DOTALL | re.IGNORECASE)
    json_match = output_pattern.search(raw_output)

    content_to_parse = ""
    if json_match:
        content_to_parse = json_match.group(1).strip()
        content_to_parse = re.sub(r'^(json\s*)', '', content_to_parse, flags=re.IGNORECASE)
        content_to_parse = re.sub(r'```json\s*|```', '', content_to_parse, flags=re.IGNORECASE).strip()
    else:
        print("警告：未找到 <output> 标签，尝试直接解析原始输出。")
        # 同样清理一下可能存在的 markdown
        content_to_parse = re.sub(r'```json\s*|```', '', raw_output.strip(), flags=re.IGNORECASE).strip()


    if not content_to_parse:
        print("错误：清理后无内容可解析。")
        return []

    try:
        parsed_data = json.loads(content_to_parse)
        structured_records = []

        if isinstance(parsed_data, list):
            # --- 处理直接列表输入 ---
            # 假设格式: [{ "table_name": ..., "fields": {...} }, ...]
            print("检测到直接列表输入格式。")
            for item in parsed_data:
                if isinstance(item, dict) and "table_name" in item and "fields" in item and isinstance(item["fields"], dict):
                    # 基本格式正确，直接添加
                    structured_records.append({
                        "table_name": item["table_name"],
                        "fields": item["fields"]
                    })
                else:
                    # 如果列表项格式不对，记录警告并跳过
                    print(f"警告：列表中的项目格式无效（缺少'table_name'或'fields'，或'fields'不是字典），已跳过: {item}")

        elif isinstance(parsed_data, dict) and "result" in parsed_data:
            # --- 处理原始期望的字典输入 ---
            # 假设格式: {"result": {"table_name": [{...}, ...]}}
            print("检测到 'result' 字典输入格式。")
            result_dict = parsed_data.get("result", {}) # 使用 .get 以防 "result" 值为 null
            if isinstance(result_dict, dict):
                for table_name, records in result_dict.items():
                    if not isinstance(records, list):
                        # 将单个记录包装成列表以便统一处理
                        print(f"警告：表 '{table_name}' 的记录不是列表，尝试包装。")
                        records = [records]
                    for record_fields in records:
                        if isinstance(record_fields, dict):
                            # 转换为统一格式
                            structured_records.append({
                                "table_name": table_name,
                                "fields": record_fields
                            })
                        else:
                             print(f"警告：表 '{table_name}' 中的记录不是字典：{record_fields}")
            else:
                 print(f"错误：解析出的 'result' 的值不是字典：{result_dict}")
                 # 返回空列表，因为无法处理非字典的 result
                 return []
        else:
            # 如果顶层结构既不是列表也不是包含 'result' 的字典
            print(f"错误：无法识别的顶层 JSON 结构。内容: '{content_to_parse[:100]}...'")
            return [] # 返回空列表

        # 处理完成后检查是否有有效记录
        if not structured_records:
             print("警告：处理后未生成任何有效的结构化记录。")

        print(f"结构化记录: {structured_records}")
        return structured_records

    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e} - 内容: '{content_to_parse[:100]}...'")
        return []
    except Exception as e:
        # 捕获其他潜在错误，例如在处理字典/列表时发生意外
        print(f"处理 LLM 输出时发生意外错误: {e}")
        return []

def extract_placeholders(structured_records: List[Dict[str, Any]]) -> Set[str]:
    """
    从结构化记录中提取所有占位符 ( {{...}} )
    对应 Dify Code `1744237287609` 的逻辑 (已调整模式)。

    Args:
        structured_records: 结构化的记录列表。

    Returns:
        一个包含所有唯一占位符内容字符串 (例如 "db(SELECT ...)", "random(string)") 的集合。
    """
    placeholders: Set[str] = set()
    if not structured_records:
        return placeholders

    for record in structured_records:
        fields = record.get("fields", {})
        for value in fields.values():
            if isinstance(value, str):
                # 使用更新后的 PLACEHOLDER_PATTERN
                matches = PLACEHOLDER_PATTERN.findall(value)
                for match in matches:
                    # match 现在是 {{...}} 内部的内容
                    placeholders.add(match.strip()) # 添加括号内的内容, 并去除前后空格
    print(f"提取到的占位符内容: {placeholders}")
    return placeholders

def process_placeholders(structured_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    遍历结构化记录，查找并处理 {{...}} 占位符。
    - {{db(SQL)}}: 执行 SQL 查询并替换为结果 (假设返回单值)。
    - {{random(type)}}: 生成指定类型的随机值 (string, integer, uuid) 并替换。
    - {{new(...)}}: 保留原样。

    Args:
        structured_records: 从 clean_and_structure_llm_add_output 返回的记录列表。

    Returns:
        处理完成的记录列表，准备提交给 API。

    Raises:
        ValueError: 如果 db 查询失败、未返回结果或 random 类型无效。
        Exception: 其他执行错误。
    """
    print("--- 处理占位符替换 ({{...}} format) ---")
    processed_records = []

    # 提取所有需要处理的占位符及其位置，避免重复查询/生成
    placeholders_to_resolve: Dict[str, Any] = {} # Map placeholder content -> resolved value
    placeholders_in_records: List[Dict[str, Any]] = [] # Store record index, field, full placeholder string

    for idx, record in enumerate(structured_records):
        fields = record.get("fields", {})
        for field, value in fields.items():
            if isinstance(value, str):
                # finditer 返回匹配对象，包含位置信息，方便替换
                for match in PLACEHOLDER_PATTERN.finditer(value):
                    full_placeholder = match.group(0) # e.g., "{{db(SELECT ...)}}"
                    placeholder_content = match.group(1).strip() # e.g., "db(SELECT ...)"
                    # 记录占位符信息以供后续处理
                    placeholders_in_records.append({
                        "record_idx": idx,
                        "field": field,
                        "full_placeholder": full_placeholder,
                        "content": placeholder_content
                    })
                    # 如果尚未解析，则添加到待解析字典
                    if placeholder_content not in placeholders_to_resolve:
                         placeholders_to_resolve[placeholder_content] = None # Mark as unresolved

    # 解析所有唯一的占位符内容
    for content, current_value in placeholders_to_resolve.items():
        if current_value is not None: # Already resolved (e.g., duplicate placeholder)
            continue

        print(f"  Resolving placeholder content: {content}")
        resolved_value = None
        try:
            if content.startswith("db(") and content.endswith(")"):
                sql = content[3:-1].strip()
                if not sql:
                     raise ValueError("db() placeholder contains empty SQL query.")
                print(f"    Executing DB query: {sql}")
                result_str = execute_query(sql) # Call API client
                if is_query_result_empty(result_str):
                     raise ValueError(f"Query returned no results for: {sql}")
                # 假设查询返回 [{ "column_name": value }]
                result_list = json.loads(result_str)
                if not result_list:
                     raise ValueError(f"Query returned empty list for: {sql}")
                first_row = result_list[0]
                if not first_row:
                     raise ValueError(f"Query returned empty row for: {sql}")
                # 取第一行的第一个值
                resolved_value = str(next(iter(first_row.values())))
                print(f"    -> DB result: {resolved_value}")

            elif content.startswith("random(") and content.endswith(")"):
                rand_type = content[7:-1].strip().lower()
                print(f"    Generating random value of type: {rand_type}")
                if rand_type == "string":
                     # Generate a simple 8-char alphanumeric string
                     chars = string.ascii_letters + string.digits
                     resolved_value = ''.join(random.choice(chars) for _ in range(8))
                elif rand_type == "integer":
                     # Generate a random 6-digit integer
                     resolved_value = str(random.randint(100000, 999999))
                elif rand_type == "uuid":
                     resolved_value = str(uuid.uuid4())
                else:
                     raise ValueError(f"Unsupported random type: {rand_type}")
                print(f"    -> Random value: {resolved_value}")

            elif content.startswith("new(") and content.endswith(")"):
                 print(f"    Keeping 'new' placeholder: {content}")
                 resolved_value = f"{{{{{content}}}}}" # Keep the full placeholder

            else:
                 # 如果不是已知类型，可以选择报错或保留原样
                 # Dify 的代码似乎会报错，我们也选择报错
                 print(f"    Unrecognized placeholder content type: {content}")
                 raise ValueError(f"无法识别的占位符内容: {content}")

            placeholders_to_resolve[content] = resolved_value

        except ValueError as ve: # Catch specific ValueErrors from processing
            print(f"  Error resolving placeholder '{content}': {ve}")
            raise # Re-raise to stop processing this record set
        except Exception as e:
            print(f"  Unexpected error resolving placeholder '{content}': {e}")
            # Wrap other exceptions in ValueError to signal failure
            raise ValueError(f"处理占位符 '{content}' 时出错: {e}") from e


    # 创建新的记录列表，用解析/生成的值替换占位符
    # 使用 deepcopy 可能更安全，但这里简化处理，假设不修改原始 records
    processed_records = [record.copy() for record in structured_records]
    for p_info in placeholders_in_records:
        record_idx = p_info["record_idx"]
        field = p_info["field"]
        full_placeholder = p_info["full_placeholder"]
        content = p_info["content"]

        resolved_value = placeholders_to_resolve.get(content)

        # 获取当前字段的值（可能已被其他占位符部分替换）
        current_field_value = processed_records[record_idx]["fields"][field]

        if resolved_value is not None and isinstance(current_field_value, str):
             # 替换字段值中的特定占位符
             # 注意: 如果一个字段中有多个相同的占位符，都会被替换
             updated_value = current_field_value.replace(full_placeholder, str(resolved_value))
             processed_records[record_idx]["fields"][field] = updated_value
             print(f"  Record {record_idx}, Field '{field}': Replaced '{full_placeholder}' with '{resolved_value}' -> '{updated_value}'")
        elif resolved_value is None:
             # 这理论上不应该发生，因为我们在前面处理了所有占位符
             # 但作为保险，如果没找到解析值，记录警告
             print(f"警告: 在记录 {record_idx} 字段 '{field}' 中找不到占位符 '{content}' 的解析值。")


    print(f"处理后的记录: {processed_records}")
    return processed_records 