# nodes/flow_control_actions.py: 包含主要流程控制相关的动作节点。

from typing import Dict, Any, List
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
    print("---节点: 处理重置意图---")
    # 同时也清空新增和删除相关状态
    return {
        "content_modify": None,
        "delete_show": None,
        "lastest_content_production": None,
        "delete_array": None,
        "content_new": None,
        "save_content": None,
        "raw_add_llm_output": None,
        "structured_add_records": None,
        "add_error_message": None,
        "raw_modify_llm_output": None,
        "modify_context_sql": None,
        "modify_context_result": None,
        "modify_error_message": None,
        # ... 其他可能需要重置的状态 ...
        "final_answer": "之前的操作状态已重置。"
    }

def handle_modify_intent_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理修改意图 (占位符)。"""
    print("---节点: 处理修改意图 (占位符)---")
    return {"final_answer": "收到修改请求 (功能待实现)。"}

def handle_add_intent_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理新增意图 (占位符)。"""
    print("---节点: 处理新增意图 (占位符)---")
    return {"final_answer": "收到新增请求 (功能待实现)。"}

def handle_delete_intent_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理删除意图 (占位符)。"""
    print("---节点: 处理删除意图 (占位符)---")
    return {"final_answer": "收到删除请求 (功能待实现)。"}

def handle_confirm_other_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理确认或其他意图 (占位符)。"""
    print("---节点: 处理确认/其他意图 (占位符)---")
    return {"final_answer": "收到确认或其他请求 (功能待实现)。"}

"""
包含与主流程控制（非初始化、非查询/分析）相关的动作节点函数。
例如：暂存操作、调用 API、清空状态、生成最终回复等。
"""
# 可以在这里添加后续的动作节点函数

# --- 保存确认流程动作节点 ---

def stage_modify_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：暂存【修改】操作，并向用户请求确认。
    对应 Dify 节点: '1742272935164' (赋值) + '1742272958774' (回复)
    """
    print("---节点: 暂存修改操作---")
    content_to_modify = state.get("content_modify", "")
    lastest_content_production = state.get("lastest_content_production")
    
    if not content_to_modify or not lastest_content_production:
         print("错误：无法暂存修改，缺少预览内容或待生产数据。")
         # 可以路由到 handle_nothing_to_stage 或设置错误
         return {"error_message": "无法暂存修改操作，缺少必要内容。"}
         
    # 注意: lastest_content_production 应该是在修改流程中准备好的 API 负载
    # 此处仅设置标记和最终提问
    confirmation_message = f"以下是即将【修改】的信息，请确认，并回复'是'/'否'\n\n{content_to_modify}"
    return {
        "save_content": "修改路径",
        "final_answer": confirmation_message
        # lastest_content_production 已由修改流程设置，此处不修改
    }

def stage_add_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：暂存【新增】操作，并向用户请求确认。
    对应 Dify 节点: '1742438351562' (赋值) + '1742438384982' (赋值) + '1742438414307' (回复)
    """
    print("---节点: 暂存新增操作---")
    content_to_add = state.get("content_new") # 用户预览文本
    lastest_content_production = state.get("lastest_content_production") # 待提交API的数据

    if not content_to_add or not lastest_content_production:
        print("错误：无法暂存新增，缺少预览内容或待生产数据。")
        return {"error_message": "无法暂存新增操作，缺少必要内容。"}

    confirmation_message = f"以下是即将【新增】的信息，请确认，并回复'是'/'否'\n\n{content_to_add}"
    return {
        "save_content": "新增路径",
        "final_answer": confirmation_message
        # lastest_content_production 已由新增流程设置
    }

def handle_nothing_to_stage_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：处理无法确定要暂存哪个操作的情况。
    """
    print("---节点: 处理无法暂存操作---")
    return {
        "final_answer": "抱歉，当前没有可以保存或确认的操作。请先进行修改、新增或删除操作。"
    }

def handle_invalid_save_state_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：处理 save_content 与实际状态不符的情况。
    """
    print("---节点: 处理无效保存状态---")
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
    print("---节点: 取消保存操作---")
    return {
        "save_content": None,
        "final_answer": "由于未收到明确保存指令，保存进程终止，你可以继续编辑内容，或输入'保存'重启保存流程"
    }

def execute_operation_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：执行暂存的操作（修改或新增），调用相应 API。
    """
    save_content = state.get("save_content")
    api_call_result = None
    error_message = None

    print(f"---节点: 执行操作 (类型: {save_content})---")

    if save_content == "修改路径":
        # --- 执行修改 --- 
        latest_production = state.get("lastest_content_production")
        if not latest_production:
            error_message = "执行修改失败：缺少待处理的负载数据。"
            print(error_message)
            return {"error_message": error_message, "api_call_result": None}

        flask_payload = latest_production 
        if not isinstance(flask_payload, list):
             error_message = "执行修改失败：待处理的负载数据格式不正确（应为列表）。"
             print(error_message)
             return {"error_message": error_message, "api_call_result": None}

        try:
            print(f"调用 API /update_record, payload: {flask_payload}")
            api_call_result = api_client.update_record(flask_payload)
            print(f"API 调用结果: {api_call_result}")
            # 检查 API 返回错误
            if isinstance(api_call_result, list) and any("error" in item for item in api_call_result):
                first_error = next((item["error"] for item in api_call_result if "error" in item), "未知 API 错误")
                error_message = f"API 更新操作部分或全部失败: {first_error}"
            elif isinstance(api_call_result, dict) and "error" in api_call_result:
                error_message = f"API 更新操作失败: {api_call_result['error']}"

            if error_message: print(error_message)

        except Exception as e:
            error_message = f"执行修改 API 调用时发生错误: {e}"
            print(error_message)
            api_call_result = {"error": error_message}
            
    elif save_content == "新增路径":
        # --- 执行新增 ---
        # 修改：直接从 lastest_content_production 获取处理后的 List[Dict]
        latest_production = state.get("lastest_content_production") 
        # 移除: add_processed_records = state.get("add_processed_records") # 这不再需要

        if latest_production is None: # 检查 None
            error_message = "执行新增失败：缺少处理后的记录 (lastest_content_production is None)。"
            print(error_message)
            return {"error_message": error_message, "api_call_result": None}
        if not isinstance(latest_production, list):
            error_message = f"执行新增失败：处理后的记录格式不正确 (lastest_content_production 应为列表，实际为 {type(latest_production)})。"
            print(error_message)
            return {"error_message": error_message, "api_call_result": None}
        if not latest_production: # 检查列表是否为空
            error_message = "执行新增失败：没有需要新增的记录 (lastest_content_production is empty)。"
            print(error_message)
            return {"error_message": error_message, "api_call_result": None}

        # 提取 API 需要的 List[Dict] (只包含字段部分) -> 修改：直接传递完整的记录列表
        # 现在 latest_production 本身就是结构化的 List[Dict[str, Any]]
        # 假设格式是 [{ "table_name": ..., "fields": {...} }, ...]
        # 我们只需要提取 "fields" 部分 -> 错误，API 需要完整的结构
        # flask_payload = []
        # for record in latest_production:
        #     if isinstance(record, dict) and "fields" in record and isinstance(record["fields"], dict):
        #         flask_payload.append(record["fields"])
        #     else:
        #          print(f"警告：跳过格式不正确的记录进行新增：{record}")
        
        # if not flask_payload:
        #      error_message = "执行新增失败：无法从处理后的记录 (lastest_content_production) 中提取有效的待插入数据。"
        #      print(error_message)
        #      return {"error_message": error_message, "api_call_result": None}

        # 直接使用 latest_production 作为 payload
        flask_payload = latest_production

        # 正确的 try...except 结构
        try:
            print(f"调用 API /insert_record, payload: {flask_payload}")
            api_call_result = api_client.insert_record(flask_payload)
            print(f"API 调用结果: {api_call_result}")

        except Exception as e:
            # 捕获 API 调用本身的异常
            error_message = f"执行新增 API 调用时发生错误: {e}"
            print(error_message)
            api_call_result = {"error": error_message} # 记录错误到结果中

    # elif save_content == "删除路径":
        # ... (未来实现)

    else:
        # 处理未知的 save_content 类型
        if save_content:
             error_message = f"执行操作失败：未知的 save_content 类型 '{save_content}'。"
        else:
             error_message = "执行操作失败：未指定操作类型 (save_content 为空)。"
        print(error_message)

    # 返回结果
    return {
        "api_call_result": json.dumps(api_call_result) if api_call_result is not None else None, 
        "error_message": error_message # 返回检测到的错误或 None
    }

def reset_after_operation_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：操作完成后，清空相关状态。
    根据 save_content 清理对应流程的状态。
    """
    save_content = state.get("save_content")
    print(f"---节点: 重置操作后状态 (类型: {save_content})---")
    
    update_dict = {
        "save_content": None,
        # "api_call_result": None # 保留给 format_response
    }
    
    if save_content == "修改路径":
        update_dict["content_modify"] = None
        update_dict["raw_modify_llm_output"] = None
        update_dict["modify_context_sql"] = None
        update_dict["modify_context_result"] = None
        update_dict["modify_error_message"] = None
        update_dict["lastest_content_production"] = None # 清空修改负载
    elif save_content == "新增路径":
        update_dict["content_new"] = None
        update_dict["raw_add_llm_output"] = None
        update_dict["structured_add_records"] = None
        update_dict["add_error_message"] = None
        update_dict["lastest_content_production"] = None # 清空新增负载
    elif save_content == "删除路径":
        update_dict["delete_show"] = None
        update_dict["delete_context_sql"] = None
        update_dict["delete_array"] = None # 清空删除负载
        
    # 总是尝试清理 lastest_content_production 以防万一
    if "lastest_content_production" not in update_dict:
         update_dict["lastest_content_production"] = None
        
    return update_dict

def format_operation_response_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：格式化操作（修改/新增/删除）的最终回复。
    """
    print("---节点: 格式化操作回复---")
    api_result_str = state.get("api_call_result")
    error_message = state.get("error_message") # 获取执行阶段的错误
    save_content = state.get("save_content") # 获取操作类型 (例如: '修改路径', '新增路径')
    query = state.get("query", "") # 获取原始用户查询
    final_answer = "操作已提交。"
    op_type_str = {"修改路径": "修改", "新增路径": "新增", "删除路径": "删除"}.get(save_content, "未知操作")

    # 优先显示执行阶段产生的错误信息
    if error_message:
        # 这里可以考虑是否也用 LLM 美化错误信息，但目前保持直接显示
        final_answer = f"抱歉，处理您的 {op_type_str} 请求时遇到问题：\n{error_message}"
        print(f"返回执行阶段错误信息: {final_answer}")
        # 保持错误信息状态可能有助于调试，暂时不清除
        return {"final_answer": final_answer}

    # 如果没有执行错误，尝试使用 LLM 格式化成功信息
    if api_result_str:
        try:
            api_result = json.loads(api_result_str)

            # 调用 llm_flow_control_service 中的 format_api_result 函数
            print(f"调用 LLM 格式化 API 结果 (类型: {op_type_str})...")
            # 将 LLM 调用移到 try 块内部
            final_answer = llm_flow_control_service.format_api_result(
                result=api_result,
                original_query=query,
                operation_type=op_type_str # 传递更友好的操作类型字符串
            )
            print(f"LLM 格式化后的回复: {final_answer}")

        except json.JSONDecodeError as e:
            # 这个 except 块现在紧跟 try
            print(f"解析 API 结果 JSON 时出错: {e}。结果字符串: {api_result_str}")
            final_answer = f"{op_type_str} 操作已提交，但无法解析 API 返回结果。请在后台确认。"
        except Exception as e:
            # 这个 except 块也紧跟 try
            # 捕获 LLM 调用或其他意外错误
            print(f"调用 LLM 格式化 API 结果时出错: {e}")
            # 使用备用消息
            final_answer = f"{op_type_str} 操作已成功提交，但在生成最终回复时遇到问题。请在数据库中确认结果。"
            
    else: # 这个 else 对应 if api_result_str:
        # 如果 API 结果为空，但也没有错误信息
        print("警告：API 结果为空且无错误信息，将返回通用成功消息。")
        final_answer = f"{op_type_str} 操作已提交。请在后台确认结果。"

    # 清理本次操作的错误信息（如果执行成功到这里）
    return {"final_answer": final_answer, "error_message": None} 