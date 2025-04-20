# data_processor.py: 包含用于数据清理、转换和状态更新的工具函数。

from typing import List

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