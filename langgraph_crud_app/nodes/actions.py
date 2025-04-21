# actions.py: 包含执行具体动作 (例如调用服务) 的 LangGraph 节点函数。 

import json
from typing import Dict, Any, List

# 导入状态定义和所需的服务函数
# 使用绝对导入路径，假设 langgraph_crud_app 在 sys.path 中
from langgraph_crud_app.graph.state import GraphState
from langgraph_crud_app.services import api_client, llm_service, data_processor

# --- 初始化流程动作节点 ---

def fetch_schema_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：调用 API 获取数据库 Schema。
    对应 Dify 节点: '1742268541036' (表结构获取)

    Args:
        state: 当前图状态。

    Returns:
        一个字典，包含要更新的状态字段 (raw_schema_result 或 error_message)。
    """
    print("---节点: 获取 Schema---")
    try:
        raw_schema_result = api_client.get_schema()
        print(f"Schema 获取成功: {raw_schema_result}")
        return {"raw_schema_result": raw_schema_result, "error_message": None}
    except Exception as e:
        error_msg = f"获取 Schema 失败: {str(e)}"
        print(error_msg)
        return {"error_message": error_msg}

def extract_table_names_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：使用 LLM 从原始 Schema 中提取表名。
    对应 Dify 节点: '1742697648839' (获取表名)

    Args:
        state: 当前图状态。

    Returns:
        一个字典，包含要更新的状态字段 (raw_table_names_str 或 error_message)。
    """
    print("---节点: 提取表名---")
    raw_schema = state.get("raw_schema_result")
    if not raw_schema:
        error_msg = "无法提取表名：原始 Schema 缺失。"
        print(error_msg)
        # 虽然 Dify 中此节点前没有明确错误处理，但这里加上更健壮
        return {"error_message": error_msg}

    try:
        table_names_str = llm_service.extract_table_names(raw_schema)
        print(f"LLM 提取的表名 (原始字符串):\n{table_names_str}")
        if not table_names_str:
             print("警告: LLM 未能提取到任何表名。")
             # 即使为空也继续，后续步骤会处理空列表
        return {"raw_table_names_str": table_names_str, "error_message": None}
    except Exception as e:
        # LLM 服务内部通常会处理异常并返回默认值，但这里再加一层保险
        error_msg = f"LLM 提取表名时出错: {str(e)}"
        print(error_msg)
        # Dify 中 LLM 失败通常不会中断流程，而是返回空结果，这里模拟该行为
        return {"raw_table_names_str": "", "error_message": error_msg} # 记录错误但仍提供空字符串

def process_table_names_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：将换行符分隔的表名字符串转换为列表。
    对应 Dify 节点: '1743382507830' (转换数组)

    Args:
        state: 当前图状态。

    Returns:
        一个字典，包含要更新的状态字段 (table_names)。
    """
    print("---节点: 处理表名列表---")
    raw_names = state.get("raw_table_names_str", "") # 从状态获取，默认为空字符串
    table_list = data_processor.nl_string_to_list(raw_names)
    # 清理可能由 LLM 添加的 markdown 代码块标记
    cleaned_list = [name for name in table_list if name.strip() != '```']
    print(f"处理后的表名列表: {cleaned_list}")
    return {"table_names": cleaned_list} # 即使列表为空也更新

def format_schema_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：使用 LLM 将原始 Schema 格式化为干净的 JSON 字符串。
    对应 Dify 节点: '1742268574820' (整理表结构信息)

    Args:
        state: 当前图状态。

    Returns:
        一个字典，包含要更新的状态字段 (biaojiegou_save 或 error_message)。
    """
    print("---节点: 格式化 Schema---")
    raw_schema = state.get("raw_schema_result")
    if not raw_schema:
        error_msg = "无法格式化 Schema：原始 Schema 缺失。"
        print(error_msg)
        return {"error_message": error_msg}

    try:
        formatted_schema = llm_service.format_schema(raw_schema)
        print(f"LLM 格式化后的 Schema: {formatted_schema}")
        if formatted_schema == "{}":
            print("警告: LLM 返回了空的 Schema 对象。")
            # 流程可能仍需继续，让后续步骤处理空 Schema
        return {"biaojiegou_save": formatted_schema, "error_message": None}
    except Exception as e:
        error_msg = f"LLM 格式化 Schema 时出错: {str(e)}"
        print(error_msg)
        # 返回空 JSON 字符串以允许流程（可能）继续
        return {"biaojiegou_save": "{}", "error_message": error_msg}

def fetch_sample_data_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：为每个表获取一条数据示例。
    对应 Dify 节点: '1742695585674' (数据示例) - 注意：Dify 此节点似乎也解析了 schema，这里简化为仅获取数据。

    Args:
        state: 当前图状态。

    Returns:
        一个字典，包含要更新的状态字段 (data_sample 或 error_message)。
    """
    print("---节点: 获取数据示例---")
    table_names = state.get("table_names")
    if not table_names:
        print("没有表名可供查询数据示例，跳过此步骤。")
        return {"data_sample": "{}"} # 返回空 JSON 对象字符串

    sample_data_dict: Dict[str, List[Dict[str, Any]]] = {}
    errors = []

    for table in table_names:
        try:
            sql = f"SELECT * FROM `{table}` LIMIT 1" # 使用反引号以防表名是关键字
            print(f"为表 '{table}' 执行查询: {sql}")
            # api_client.execute_query 返回 JSON 字符串，需要解析
            result_str = api_client.execute_query(sql)
            result_list = json.loads(result_str) # 解析 JSON 字符串为列表
            sample_data_dict[table] = result_list if result_list else [] # 如果查询无结果，存空列表
            print(f"表 '{table}' 的示例数据获取成功: {result_list}")
        except Exception as e:
            error_msg = f"为表 '{table}' 获取示例数据时失败: {str(e)}"
            print(error_msg)
            errors.append(error_msg)
            sample_data_dict[table] = [{"error": error_msg}] # 在结果中记录错误

    # 将所有表的样本数据汇总成一个 JSON 字符串
    final_sample_str = json.dumps(sample_data_dict, ensure_ascii=False, indent=2) # indent 用于可读性
    print(f"最终的数据示例 JSON 字符串: {final_sample_str}")

    # 如果在获取任何样本数据时出错，也记录一个聚合错误信息
    aggregated_error = "; ".join(errors) if errors else None

    return {"data_sample": final_sample_str, "error_message": aggregated_error}

# --- 其他流程的动作节点 (占位) ---
# def classify_main_intent_action(state: GraphState) -> Dict[str, Any]:
#     print("---节点: 分类主要意图---")
#     # ... 调用 llm_service.classify ...
#     return {}

# 其他函数和代码块保持不变
# ... 