# nodes/preprocessing_actions.py: 包含初始化流程的动作节点。

import json
from typing import Dict, Any, List

# 导入状态定义和所需的服务函数
from langgraph_crud_app.graph.state import GraphState
from langgraph_crud_app.services import api_client, data_processor
from langgraph_crud_app.services import llm_preprocessing_service # 仅导入前置处理服务

# --- 初始化流程动作节点 ---

def fetch_schema_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：调用 API 获取数据库 Schema。"""
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
    """节点动作：使用 LLM 从原始 Schema 中提取表名。"""
    print("---节点: 提取表名---")
    raw_schema = state.get("raw_schema_result")
    if not raw_schema:
        error_msg = "无法提取表名：原始 Schema 缺失。"
        print(error_msg)
        return {"error_message": error_msg}
    try:
        table_names_str = llm_preprocessing_service.extract_table_names(raw_schema)
        print(f"LLM 提取的表名 (原始字符串):\n{table_names_str}")
        if not table_names_str:
             print("警告: LLM 未能提取到任何表名。")
        return {"raw_table_names_str": table_names_str, "error_message": None}
    except Exception as e:
        error_msg = f"LLM 提取表名时出错: {str(e)}"
        print(error_msg)
        return {"raw_table_names_str": "", "error_message": error_msg}

def process_table_names_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：将换行符分隔的表名字符串转换为列表。"""
    print("---节点: 处理表名列表---")
    raw_names = state.get("raw_table_names_str", "")
    table_list = data_processor.nl_string_to_list(raw_names)
    cleaned_list = [name for name in table_list if name.strip() != '```']
    print(f"处理后的表名列表: {cleaned_list}")
    return {"table_names": cleaned_list}

def format_schema_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：使用 LLM 将原始 Schema 格式化为干净的 JSON 字符串。"""
    print("---节点: 格式化 Schema---")
    raw_schema = state.get("raw_schema_result")
    if not raw_schema:
        error_msg = "无法格式化 Schema：原始 Schema 缺失。"
        print(error_msg)
        return {"error_message": error_msg}
    try:
        formatted_schema = llm_preprocessing_service.format_schema(raw_schema)
        print(f"LLM 格式化后的 Schema: {formatted_schema}")
        if formatted_schema == "{}":
            print("警告: LLM 返回了空的 Schema 对象。")
        return {"biaojiegou_save": formatted_schema, "error_message": None}
    except Exception as e:
        error_msg = f"LLM 格式化 Schema 时出错: {str(e)}"
        print(error_msg)
        return {"biaojiegou_save": "{}", "error_message": error_msg}

def fetch_sample_data_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：为每个表获取一条数据示例。"""
    print("---节点: 获取数据示例---")
    table_names = state.get("table_names")
    if not table_names:
        print("没有表名可供查询数据示例，跳过此步骤。")
        return {"data_sample": "{}"}
    sample_data_dict: Dict[str, List[Dict[str, Any]]] = {}
    errors = []
    for table in table_names:
        try:
            sql = f"SELECT * FROM `{table}` LIMIT 1"
            print(f"为表 '{table}' 执行查询: {sql}")
            result_str = api_client.execute_query(sql)
            result_list = json.loads(result_str)
            sample_data_dict[table] = result_list if result_list else []
            print(f"表 '{table}' 的示例数据获取成功: {result_list}")
        except Exception as e:
            error_msg = f"为表 '{table}' 获取示例数据时失败: {str(e)}"
            print(error_msg)
            errors.append(error_msg)
            sample_data_dict[table] = [{"error": error_msg}]
    final_sample_str = json.dumps(sample_data_dict, ensure_ascii=False, indent=2)
    print(f"最终的数据示例 JSON 字符串: {final_sample_str}")
    aggregated_error = "; ".join(errors) if errors else None
    return {"data_sample": final_sample_str, "error_message": aggregated_error} 