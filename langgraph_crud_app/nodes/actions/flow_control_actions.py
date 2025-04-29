# nodes/flow_control_actions.py: 包含主要流程控制相关的动作节点。

from typing import Dict, Any
import json # 新增导入

# 导入状态定义
from langgraph_crud_app.graph.state import GraphState
# 导入服务
from langgraph_crud_app.services import api_client # 新增导入
from langgraph_crud_app.services.llm import llm_flow_control_service # 新增导入

# --- 主流程占位符/简单动作节点 ---

def handle_reset_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：处理重置意图。
    对应 Dify 节点: '1742436161345' (重置检索结果)
    """
    print("---节点: 处理重置意图--- marginalised")
    return {
        "content_modify": None,
        "delete_show": None,
        "lastest_content_production": [],
        "content_new": None,
        "save_content": None,
        "final_answer": "之前的检索状态已重置。"
    }

def handle_modify_intent_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理修改意图 (占位符)。"""
    print("---节点: 处理修改意图 (占位符)--- marginalised")
    return {"final_answer": "收到修改请求 (功能待实现)。"}

def handle_add_intent_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理新增意图 (占位符)。"""
    print("---节点: 处理新增意图 (占位符)--- marginalised")
    return {"final_answer": "收到新增请求 (功能待实现)。"}

def handle_delete_intent_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理删除意图 (占位符)。"""
    print("---节点: 处理删除意图 (占位符)--- marginalised")
    return {"final_answer": "收到删除请求 (功能待实现)。"}

def handle_confirm_other_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理确认或其他意图 (占位符)。"""
    print("---节点: 处理确认/其他意图 (占位符)--- marginalised")
    return {"final_answer": "收到确认或其他请求 (功能待实现)。"}

"""
包含与主流程控制（非初始化、非查询/分析）相关的动作节点函数。
例如：暂存操作、调用 API、清空状态、生成最终回复等。
"""
# 可以在这里添加后续的动作节点函数

# --- 保存确认流程动作节点 ---

def stage_modify_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：暂存修改操作，并向用户请求确认。
    对应 Dify 节点: '1742272935164' (赋值) + '1742272958774' (回复)
    """
    print("---节点: 暂存修改操作--- marginalised")
    content_to_modify = state.get("content_modify", "")
    # TODO: 实际应用中，content_modify 的格式可能需要调整或美化后再展示给用户
    confirmation_message = f"以下是即将保存的信息，请确认，并回复是/否进行修改\n\n{content_to_modify}"
    return {
        "save_content": "修改路径",
        "final_answer": confirmation_message
    }

def handle_nothing_to_stage_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：处理无法确定要暂存哪个操作的情况。
    """
    print("---节点: 处理无法暂存操作--- marginalised")
    return {
        "final_answer": "抱歉，当前没有可以保存或确认的操作。请先进行修改、新增或删除操作。"
    }

def handle_invalid_save_state_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：处理 save_content 与实际状态不符的情况。
    """
    print("---节点: 处理无效保存状态--- marginalised")
    # 清理可能不一致的状态
    return {
        "save_content": None,
        "final_answer": "抱歉，当前的保存状态似乎有些混乱，请重新发起您的操作。"
    }

def cancel_save_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：用户取消保存/确认操作。
    对应 Dify 节点: '1742350702992' (赋值) + '1742350737329' (回复)
    """
    print("---节点: 取消保存操作--- marginalised")
    return {
        "save_content": None,
        "final_answer": "由于未收到明确保存指令，保存进程终止，你可以继续编辑内容，或输入'保存'重启保存流程"
    }

# execute_modify_action, reset_after_modify_action, format_modify_response_action 等将在后续添加
def execute_modify_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：执行修改操作，调用 API。
    对应 Dify 节点: '1742351513942' (LLM) + '1742354001584' (Code)
    **简化点**: 假设 state['content_modify'] 已包含 API 所需的 JSON 格式。
    """
    print("---节点: 执行修改操作--- marginalised")
    content_modify_str = state.get("content_modify")
    api_call_result = None
    error_message = None

    if not content_modify_str:
        error_message = "执行修改失败：缺少修改内容 (content_modify is empty)。"
        print(error_message)
        return {"error_message": error_message, "api_call_result": None}

    try:
        # 假设 content_modify_str 是 LLM 返回的 JSON 字符串，格式为 {"table_name": [operations...]}
        try:
            llm_output_dict = json.loads(content_modify_str)
            if not isinstance(llm_output_dict, dict):
                raise ValueError("content_modify 解析后应为字典")

            # --- 数据结构转换 --- 
            # 将 { "table": [op1, op2...] } 转换为 [ {"table_name":"table", ...op1}, {"table_name":"table", ...op2} ]
            flask_payload = []
            for table_name, operations in llm_output_dict.items():
                if not isinstance(operations, list):
                    raise ValueError(f"字典中表 '{table_name}' 的值应为列表")
                for op in operations:
                    if not isinstance(op, dict):
                        raise ValueError(f"操作列表中的元素应为字典")
                    # 构建 Flask API 期望的单条更新字典
                    single_update = {
                        "table_name": table_name,
                        "primary_key": op.get("primary_key"),
                        "primary_value": op.get("primary_value"),
                        # 关键：重命名字段键 "fields" -> "update_fields"
                        "update_fields": op.get("fields", {})
                        # op 中可能存在的 "target_primary_value" 在此被忽略，因为 Flask API 不期望它
                    }
                    # 进行基本检查，确保关键信息存在
                    if not all([single_update["table_name"], single_update["primary_key"], single_update["primary_value"] is not None]):
                         raise ValueError(f"操作字典缺少 table_name, primary_key, 或 primary_value: {op}")
                    flask_payload.append(single_update)
            
            if not flask_payload:
                 raise ValueError("转换后的更新负载为空，原始数据可能无效或为空。")

        except json.JSONDecodeError as e:
            raise ValueError(f"解析 content_modify 失败: {e}")
        except ValueError as e:
            # 捕获上面转换逻辑中抛出的 ValueError
            raise ValueError(f"转换 content_modify 结构失败: {e}")

        print(f"调用 API /update_record, payload: {flask_payload}") # 使用转换后的 flask_payload
        api_call_result = api_client.update_record(flask_payload) # 传递转换后的 flask_payload
        print(f"API 调用结果: {api_call_result}")
        # 检查 API 返回是否包含错误
        if isinstance(api_call_result, list) and any("error" in item for item in api_call_result):
             # 提取第一个错误信息用于显示
             first_error = next((item["error"] for item in api_call_result if "error" in item), "未知 API 错误")
             error_message = f"API 更新操作部分或全部失败: {first_error}"
             print(error_message)
        elif isinstance(api_call_result, dict) and "error" in api_call_result:
             error_message = f"API 更新操作失败: {api_call_result['error']}"
             print(error_message)

    except Exception as e:
        error_message = f"执行修改操作时发生错误: {e}"
        print(error_message)
        api_call_result = {"error": error_message} # 统一错误格式

    # 无论成功失败，都存储 API 结果，并清除错误信息（如果 API 调用本身是成功的）
    # 如果 API 返回错误，error_message 会被设置
    return {"api_call_result": api_call_result, "error_message": error_message}

def reset_after_modify_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：修改操作完成后，清空相关状态。
    对应 Dify 节点: '17444989330050'
    """
    print("---节点: 重置修改后状态--- marginalised")
    return {
        "save_content": None,
        "content_modify": None,
        "lastest_content_production": [], # 保持一致性清空
        # "api_call_result": None # 保留 api_call_result 给下一个节点格式化
    }

def format_modify_response_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：格式化修改操作的最终回复。
    对应 Dify 节点: '1744661636396'
    """
    print("---节点: 格式化修改回复--- marginalised")
    api_result = state.get("api_call_result")
    final_answer = "修改操作已完成。"

    try:
        # 调用 LLM 服务格式化回复
        final_answer = llm_flow_control_service.format_api_result(
            result=api_result,
            original_query=state.get("query", ""), # 可能需要传递原始请求以提供上下文
            operation_type="修改"
        )
        print(f"LLM 格式化回复: {final_answer}")
    except Exception as e:
        print(f"LLM 格式化回复失败: {e}. 使用默认回复。")
        # LLM 调用失败，提供一个基于 API 结果的简单回复
        if isinstance(api_result, list) and any("error" in item for item in api_result):
            final_answer = f"修改操作遇到问题: {state.get('error_message', '详情请查看日志')}"
        elif isinstance(api_result, dict) and "error" in api_result:
             final_answer = f"修改操作失败: {api_result['error']}"
        elif api_result:
            final_answer = f"修改操作成功完成！API 返回: {json.dumps(api_result, ensure_ascii=False)}" # 简单的成功提示
        else:
            final_answer = "修改操作已执行，但未收到明确的 API 返回信息。"

    return {"final_answer": final_answer, "api_call_result": None} # 清空临时结果 