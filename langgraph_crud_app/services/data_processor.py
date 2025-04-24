# data_processor.py: 包含用于数据清理、转换和状态更新的工具函数。

from typing import List, Optional
import re # Import re for cleaning
import json # Import json

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