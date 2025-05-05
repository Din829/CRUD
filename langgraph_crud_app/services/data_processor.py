# data_processor.py: 包含用于数据清理、转换和状态更新的工具函数。

from typing import List, Optional, Dict, Any, Set
import re # Import re for cleaning
import json # Import json
import random
import string
import uuid # Add uuid import for random UUID generation
# Import API client for placeholder resolution
from .api_client import execute_query 

def is_sql_part_balanced(sql_part: str) -> bool:
    """
    检查SQL片段中的括号是否平衡。
    
    Args:
        sql_part: SQL片段
        
    Returns:
        如果括号平衡返回True，否则返回False
    """
    stack = []
    bracket_pairs = {')': '(', '}': '{', ']': '['}
    
    for char in sql_part:
        if char in '({[':
            stack.append(char)
        elif char in ')}]':
            if not stack or stack.pop() != bracket_pairs[char]:
                return False
    
    return len(stack) == 0  # 栈为空表示所有括号都匹配

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
    清理 LLM 生成的 SQL 字符串，仅移除Markdown代码块和注释，保留完整的SQL结构。
    对应 Dify code 节点 '1742268810496' 和 '17432988044960' 的逻辑。

    Args:
        sql: 可能包含多余字符的 SQL 字符串。

    Returns:
        清理后的 SQL 字符串。
    """
    if not sql:
        return ""
        
    # 记录原始SQL长度
    original_length = len(sql)
    print(f"--- 清理SQL前长度: {original_length} ---")
    
    # 移除常见的 Markdown 代码块标记
    cleaned_sql = re.sub(r'^```sql\s*', '', sql, flags=re.IGNORECASE)
    cleaned_sql = re.sub(r'^```mysql\s*', '', cleaned_sql, flags=re.IGNORECASE)
    cleaned_sql = re.sub(r'\s*```$', '', cleaned_sql)
    
    # 移除可能存在的前后空白符
    cleaned_sql = cleaned_sql.strip()
    
    # 不执行空白字符替换，保留原始格式
    # 只合并连续的多个空格为一个空格，保留换行和缩进
    # cleaned_sql = re.sub(r' {2,}', ' ', cleaned_sql)
    
    # 清理SQL注释，但保留其他所有内容
    cleaned_sql = re.sub(r'--.*?$', '', cleaned_sql, flags=re.MULTILINE)
    cleaned_sql = re.sub(r'/\*.*?\*/', '', cleaned_sql, flags=re.DOTALL)
    
    # 再次清理前后空白，但保留内部结构
    cleaned_sql = cleaned_sql.strip()
    
    # 处理分号问题，确保SQL有一个结尾分号
    has_semicolon = cleaned_sql.endswith(';')
    if not has_semicolon:
        cleaned_sql = cleaned_sql + ';'
        print("--- 为SQL添加了分号 ---")
    
    # 检查括号是否平衡，但不修改SQL内容
    if not is_sql_part_balanced(cleaned_sql):
        print("--- 警告: SQL括号不平衡，可能导致语法错误 ---")
    
    # 最终检查：确保SQL是以SELECT开头，但不修改
    if not cleaned_sql.upper().strip().startswith('SELECT'):
        print(f"--- 警告：清理后的SQL不是以SELECT开头: {cleaned_sql[:50]}... ---")
    
    # 检查WHERE子句是否存在且看起来完整
    where_match = re.search(r'\bWHERE\b\s+([^)]{1,50})$', cleaned_sql, re.IGNORECASE)
    if where_match:
        print(f"--- 警告: SQL可能在WHERE子句处不完整: '{where_match.group(0)}' ---")
    
    # 记录清理后的长度变化
    final_length = len(cleaned_sql)
    print(f"--- 清理SQL后长度: {final_length} (减少了 {original_length - final_length} 个字符) ---")
    
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
    处理结构化记录中的占位符 ( {{...}} )。
    支持 {{db(...)}} 和 {{random(...)}} 格式。
    修改：明确忽略 {{new(...)}} 格式，让其原样通过。

    Args:
        structured_records: 包含占位符的结构化记录列表。

    Returns:
        处理完占位符后的结构化记录列表。

    Raises:
        ValueError: 如果遇到不支持的占位符类型或执行查询出错。
    """
    print("--- 处理占位符替换 ({{...}} format) ---")
    processed_records = []
    # 深拷贝以避免修改原始状态？或者假设调用者处理？暂时直接修改

    for record in structured_records:
        processed_fields = {}
        if not isinstance(record, dict) or "fields" not in record or not isinstance(record["fields"], dict):
             print(f"警告：跳过格式不正确的记录（缺少 fields 或非字典）: {record}")
             processed_records.append(record) # 保留原始记录？或跳过？暂定保留
             continue

        for field, value in record["fields"].items():
            if isinstance(value, str):
                match = PLACEHOLDER_PATTERN.search(value) # 使用 search 查找单个占位符
                if match:
                    placeholder_content = match.group(1).strip()
                    print(f"  正在解析占位符: '{placeholder_content}' for field '{field}'")
                    
                    # --- 新增：忽略 {{new(...)}} --- 
                    if placeholder_content.lower().startswith("new("):
                         print(f"    忽略占位符 new(): '{placeholder_content}'")
                         processed_fields[field] = value # 保留原始值 {{new(...)}}
                         continue # 处理下一个字段
                    # --- 结束新增 --- 

                    # 处理 {{db(...)}} 
                    if placeholder_content.lower().startswith("db(") and placeholder_content.endswith(")"):
                        query = placeholder_content[3:-1].strip()
                        print(f"    占位符类型: db, 执行查询: '{query}'")
                        try:
                            query_result_str = execute_query(query)
                            query_result = json.loads(query_result_str)
                            # 假设查询只返回一行一列
                            if isinstance(query_result, list) and len(query_result) == 1 and isinstance(query_result[0], dict):
                                first_row = query_result[0]
                                if len(first_row) == 1:
                                    resolved_value = list(first_row.values())[0]
                                    print(f"    查询结果 (单值): {resolved_value}")
                                    processed_fields[field] = resolved_value
                                else:
                                    # 如果返回多列，可以选择返回整个字典或报错
                                    print(f"    警告：db 查询 '{query}' 返回了多列，将使用整个字典。")
                                    processed_fields[field] = first_row # 或者抛出错误？
                            elif isinstance(query_result, list) and not query_result: # 空列表
                                 print(f"    警告：db 查询 '{query}' 返回空结果，将使用 None。")
                                 processed_fields[field] = None # 或者空字符串 ''?
                            else:
                                raise ValueError(f"db 查询 '{query}' 的结果格式无法解析为单值: {query_result_str}")
                        except Exception as e:
                            print(f"    错误：执行 db 查询 '{query}' 或处理结果失败: {e}")
                            raise ValueError(f"处理 db 占位符失败: {e}")
                    
                    # 处理 {{random(...)}}    
                    elif placeholder_content.lower().startswith("random(") and placeholder_content.endswith(")"):
                        random_type = placeholder_content[7:-1].strip().lower()
                        print(f"    占位符类型: random, 类型: '{random_type}'")
                        resolved_value = None
                        if random_type == "string":
                            resolved_value = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                        elif random_type == "number":
                            resolved_value = random.randint(1, 1000) 
                        elif random_type == "uuid":
                            resolved_value = str(uuid.uuid4())
                        # 可以添加更多随机类型，例如 email, phone 等
                        else:
                            print(f"    错误：不支持的 random 类型 '{random_type}'")
                            raise ValueError(f"不支持的 random 类型: {random_type}")
                        print(f"    生成随机值: {resolved_value}")
                        processed_fields[field] = resolved_value
                        
                    else:
                        # 处理无法识别的占位符
                        print(f"    错误：无法识别的占位符内容: '{placeholder_content}'")
                        raise ValueError(f"无法识别的占位符内容: {placeholder_content}")
                else:
                    # 不是占位符，保留原始值
                    processed_fields[field] = value
            else:
                # 非字符串值，直接保留
                processed_fields[field] = value
        
        # 更新记录的 fields
        processed_records.append({"table_name": record["table_name"], "fields": processed_fields})

    print(f"--- 占位符处理完成。处理后记录: {processed_records} ---")
    return processed_records 