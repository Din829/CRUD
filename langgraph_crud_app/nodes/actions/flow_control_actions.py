# nodes/flow_control_actions.py: 包含主要流程控制相关的动作节点。

from typing import Dict, Any, List, Optional
import json # 新增导入

# 导入状态定义
from langgraph_crud_app.graph.state import GraphState
# 导入服务
from langgraph_crud_app.services import api_client # 新增导入
from langgraph_crud_app.services.llm import llm_flow_control_service # 新增导入
# 新增导入删除 LLM 服务
from langgraph_crud_app.services.llm import llm_delete_service

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
        # lastest_content_production 已由新增流程设置，此处不修改
    }

def stage_combined_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：暂存【复合】操作（可能包含修改、新增等），并向用户请求确认。
    """
    print("---节点: 暂存复合操作---")
    content_to_confirm = state.get("content_combined") # 获取复合预览文本
    operation_plan = state.get("lastest_content_production") # 获取复合操作计划列表

    if not content_to_confirm or not operation_plan:
        print("错误：无法暂存复合操作，缺少预览内容或操作计划。")
        return {"error_message": "无法暂存复合操作，缺少必要内容。"}
    
    if not isinstance(operation_plan, list):
         print(f"错误：无法暂存复合操作，操作计划格式不正确（应为列表，实际为 {type(operation_plan)}）。")
         return {"error_message": "无法暂存复合操作，操作计划格式错误。"}

    confirmation_message = f"以下是即将执行的【复合操作】，请确认，并回复'是'/'否'\n\n{content_to_confirm}"
    return {
        "save_content": "复合路径", # 设置新的标记
        "final_answer": confirmation_message
        # lastest_content_production (操作计划) 已由上游节点设置
    }

def stage_delete_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：暂存【删除】操作，并向用户请求确认。
    """
    print("---节点: 暂存删除操作---")
    content_to_delete = state.get("content_delete") # 获取删除预览文本

    if not content_to_delete:
        print("错误：无法暂存删除，缺少预览内容。")
        return {"error_message": "无法暂存删除操作，缺少预览内容。"}

    confirmation_message = f"请仔细检查以下将要删除的内容：\\n\\n{content_to_delete}\\n\\n请输入 '是' 确认删除，或输入 '否' 取消。"
    return {
        "save_content": "删除路径", # 设置删除标记
        "final_answer": confirmation_message
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
    节点动作：执行暂存的操作（修改、新增、复合、删除），调用相应 API。
    """
    save_content = state.get("save_content")
    api_call_result = None
    error_message = None
    updates: Dict[str, Any] = {} # 用于收集所有状态更新

    print(f"---节点: 执行操作 (类型: {save_content})---")

    try: # 将所有操作包裹在一个 try 中，简化错误处理
        if save_content == "修改路径":
            # --- 执行修改 ---
            latest_production = state.get("lastest_content_production")
            if not latest_production:
                raise ValueError("执行修改失败：缺少待处理的负载数据。")
            if not isinstance(latest_production, list):
                raise ValueError("执行修改失败：待处理的负载数据格式不正确（应为列表）。")

            print(f"调用 API /update_record, payload: {latest_production}")
            api_call_result = api_client.update_record(latest_production)
            print(f"API 调用结果: {api_call_result}")
            # 检查 API 返回错误 (通用化处理移到 try 块末尾)

        elif save_content == "新增路径":
            # --- 执行新增 ---
            latest_production = state.get("lastest_content_production")
            if latest_production is None:
                raise ValueError("执行新增失败：缺少处理后的记录 (lastest_content_production is None)。")
            if not isinstance(latest_production, list):
                raise ValueError(f"执行新增失败：处理后的记录格式不正确 (应为列表，实际为 {type(latest_production)})。")
            if not latest_production:
                raise ValueError("执行新增失败：没有需要新增的记录 (lastest_content_production is empty)。")

            print(f"调用 API /insert_record, payload: {latest_production}")
            api_call_result = api_client.insert_record(latest_production)
            print(f"API 调用结果: {api_call_result}")

        elif save_content == "复合路径":
            # --- 执行复合操作 ---
            latest_production = state.get("lastest_content_production")
            if not latest_production:
                 raise ValueError("执行复合操作失败：缺少操作计划列表。")
            if not isinstance(latest_production, list):
                 raise ValueError("执行复合操作失败：操作计划格式不正确（应为列表）。")

            print(f"调用 API /execute_batch_operations, payload: {latest_production}")
            api_call_result = api_client.execute_batch_operations(latest_production) # 调用批量接口
            print(f"API 调用结果: {api_call_result}")

        elif save_content == "删除路径":
            # --- 执行删除 ---
            print("--- 执行: 删除操作 ---")
            delete_show_json = state.get("delete_show")
            schema_info = state.get("biaojiegou_save")
            table_names = state.get("table_names")
            
            # 检查是否已经在预览步骤中确认没有找到记录
            content_delete = state.get("content_delete")
            if content_delete == "未找到需要删除的记录。":
                print("--- 预览已确认没有记录需要删除，跳过删除操作 ---")
                api_call_result = {"message": "未找到需要删除的记录。"}
                updates["api_call_result"] = api_call_result
                updates["delete_api_result"] = api_call_result
                return updates
                
            if not delete_show_json or not schema_info or not table_names:
                raise ValueError("缺少解析删除 ID 所需的信息 (delete_show, schema, table_names)")

            # 检查是否为空结果
            if delete_show_json.strip() == '[]':
                print("--- 删除预览为空列表，无需执行删除操作 ---")
                api_call_result = {"message": "未找到需要删除的记录。"}
                updates["api_call_result"] = api_call_result
                updates["delete_api_result"] = api_call_result
                return updates

            # 1. 调用直接解析函数替代LLM解析
            parsed_ids_llm_output = llm_delete_service.parse_delete_ids_direct(delete_show_json, schema_info, table_names)
            updates["delete_ids_llm_output"] = parsed_ids_llm_output # 存储解析输出

            # 2. 解析输出
            try:
                # 解析JSON输出
                temp_data = json.loads(parsed_ids_llm_output)
                structured_ids_dict = temp_data.get("result", {})
                if not isinstance(structured_ids_dict, dict):
                        raise ValueError("解析的 ID 结构不是预期的字典格式")
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(f"解析返回的删除 ID 时出错: {e}") from e

            # 存储解析后的结构化 ID
            updates["delete_ids_structured_str"] = json.dumps(structured_ids_dict, ensure_ascii=False)

            # 3. 准备并执行 API 调用
            api_results_list = [] # 重命名以避免与外层变量冲突
            if not structured_ids_dict:
                print("--- 解析后无 ID 需要删除 ---")
                api_call_result = {"message": "没有需要删除的记录。"} # 认为无操作是成功
            else:
                print(f"--- 准备删除以下 ID: {structured_ids_dict} ---")
                try:
                     schema_dict = json.loads(schema_info)
                except json.JSONDecodeError:
                     raise ValueError("无法解析 Schema 信息以获取主键")

                delete_payloads = []
                for table_name, ids_to_delete in structured_ids_dict.items():
                    if not ids_to_delete: continue
                    try:
                        table_schema = schema_dict.get(table_name, {})
                        fields = table_schema.get("fields", {})
                        primary_key = next(field for field, info in fields.items() if info.get("key") == "PRI")
                    except StopIteration:
                        api_results_list.append({"table": table_name, "error": "无法确定主键"})
                        continue
                    for id_val in ids_to_delete:
                        delete_payloads.append({
                            "table_name": table_name,
                            "primary_key": primary_key,
                            "primary_value": id_val
                        })

                # 执行删除 (逐条)
                if delete_payloads:
                    print(f"开始逐条删除 {len(delete_payloads)} 条记录...")
                    for payload in delete_payloads:
                            try:
                                result = api_client.delete_record(
                                    table_name=payload["table_name"],
                                    primary_key=payload["primary_key"],
                                    primary_value=payload["primary_value"]
                                )
                                api_results_list.append({"table": payload["table_name"], "id": payload["primary_value"], **result})
                            except Exception as api_err:
                                print(f"API delete error for {payload['table_name']} ID {payload['primary_value']}: {api_err}")
                                api_results_list.append({"table": payload["table_name"], "id": payload["primary_value"], "error": str(api_err)})
                    print("--- 逐条删除完成 ---")
                    api_call_result = api_results_list # 将列表作为结果
                else:
                    # 如果解析后发现没有有效载荷（可能因为主键错误等）
                     api_call_result = {"message": "没有有效的记录可供删除。"} if not api_results_list else api_results_list

            # 将删除结果存入特定键和通用键
            updates["delete_api_result"] = api_call_result
            updates["api_call_result"] = api_call_result  # 同时存入通用键，确保格式化响应能够正确获取结果

        else:
            error_message = f"未知的操作类型: {save_content}"
            print(error_message)
            updates["error_message"] = error_message
            updates["api_call_result"] = None # 明确设为 None
            return updates # 直接返回错误状态

        # --- 通用 API 结果检查 ---
        if api_call_result is not None:
            updates["api_call_result"] = api_call_result # 确保结果被记录
            # 检查列表类型结果中的错误
            if isinstance(api_call_result, list) and any(isinstance(item, dict) and "error" in item for item in api_call_result):
                first_error = next((item["error"] for item in api_call_result if isinstance(item, dict) and "error" in item), "未知 API 错误")
                error_message = f"API 操作部分或全部失败: {first_error}"
            # 检查字典类型结果中的错误
            elif isinstance(api_call_result, dict) and "error" in api_call_result:
                error_message = f"API 操作失败: {api_call_result['error']}"

            if error_message:
                 print(f"API 调用报告错误: {error_message}")
                 updates["error_message"] = error_message # 记录错误

        else: # 如果前面某个分支没有设置 api_call_result
             if not updates.get("error_message"): # 且没有明确错误
                 error_message = f"操作 '{save_content}' 未产生 API 调用结果。"
                 print(error_message)
                 updates["error_message"] = error_message


    except Exception as e:
        error_message = f"执行操作 '{save_content}' 时发生意外错误: {e}"
        print(error_message)
        updates["error_message"] = error_message
        updates["api_call_result"] = None # 发生异常时清空结果

    # 无论成功或失败，都返回所有更新
    return updates

def reset_after_operation_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：在成功执行操作（或即使失败，只要流程继续）后，清空相关的暂存和预览状态。
    """
    print("---节点: 操作后重置状态---")

    keys_to_reset: List[str] = [
        # "save_content", # 暂时不重置，format_operation_response_action 需要它
        # Modify related
        "content_modify",
        "modify_context_sql",
        "modify_context_result",
        "raw_modify_llm_output",
        "modify_error_message", # 清理旧流程错误
        # Add related
        "content_new",
        "temp_add_llm_data",
        "add_structured_records_str",
        "structured_add_records", # 如果还使用的话
        "add_processed_records_str",
        "add_processed_records", # 如果还使用的话
        "add_preview_text",
        "add_error_message", # 清理旧流程错误
        "add_parse_error", # 清理旧流程错误
         # Delete related - 新增
        "delete_preview_sql",
        "delete_show",
        "delete_preview_text",
        "delete_error_message", # 清理旧流程错误
        "content_delete",
        "delete_ids_llm_output",
        "delete_ids_structured_str",
        # "delete_api_result", # 不再清理删除 API 结果，确保格式化响应能获取到它
         # Composite related
        "combined_operation_plan",
        "content_combined",
        # Common execution related
        "lastest_content_production", # 清空待执行负载
        # "api_call_result", # 不再清理通用 API 结果，格式化响应需要它
        "delete_array", # 如果确认流程中还用到的话
        # ... 其他可能需要重置的中间状态 ...
        # 不重置: final_answer (由下一步生成), error_message (可能需要传递)
    ]

    updates = {key: None for key in keys_to_reset}
    print(f"重置状态键: {list(updates.keys())}")
    return updates

def format_operation_response_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：调用 LLM 格式化 API 调用结果（成功或失败）为最终回复。
    """
    print("---节点: 格式化操作响应---")
    
    # 首先检查通用结果，然后检查特定删除结果
    api_result_data = state.get("api_call_result")
    delete_api_result = state.get("delete_api_result")
    
    # 如果通用结果为空但存在删除结果，则使用删除结果
    if api_result_data is None and delete_api_result is not None:
        api_result_data = delete_api_result
        print(f"使用删除特定API结果: {api_result_data}")
    
    error_message_from_execution = state.get("error_message") # 通用执行错误
    user_query = state.get("user_query", "用户操作")
    save_content = state.get("save_content") # 获取操作类型标记

    # 日志输出
    print(f"操作类型: {save_content}")
    print(f"API结果: {api_result_data}")
    print(f"执行错误: {error_message_from_execution}")

    # 映射 save_content 到用户友好的操作类型字符串
    op_type_str = {
        "修改路径": "修改",
        "新增路径": "新增",
        "删除路径": "删除",
        "复合路径": "复合操作"
    }.get(save_content, "未知操作")

    final_answer = "操作出现未知问题。" # 默认回复

    try:
        # 修正参数传递
        if error_message_from_execution: # 如果执行层捕获了顶层错误
            print(f"格式化执行层错误信息: {error_message_from_execution}")
            final_answer = llm_flow_control_service.format_api_result(
                result=None, # 没有成功结果
                original_query=user_query,
                operation_type=op_type_str
            )
            # 如果 format_api_result 不能很好地处理顶层错误，提供回退消息
            if "未知" in final_answer:
                final_answer = f"操作失败：{error_message_from_execution}"

        elif api_result_data is not None: # 如果有 API 结果
            print(f"格式化 API 结果: {api_result_data}")
            final_answer = llm_flow_control_service.format_api_result(
                result=api_result_data, # 传递 API 结果
                original_query=user_query,
                operation_type=op_type_str
            )
            # 如果是删除操作且结果是列表
            if op_type_str == "删除" and isinstance(api_result_data, list):
                # 提供更友好的默认消息
                successful_count = sum(1 for item in api_result_data if isinstance(item, dict) and "error" not in item)
                if successful_count > 0:
                    if "未知" in final_answer:  # 如果LLM格式化失败了
                        final_answer = f"成功删除了 {successful_count} 条记录。"
        else:
            print("警告: 无法格式化响应，既无 API 结果也无错误信息。")
            if op_type_str == "删除":
                final_answer = "删除操作已执行，但无法获取具体结果。请检查数据以确认。"
            else:
                final_answer = f"{op_type_str}操作状态未知，请检查系统日志。"

    except Exception as e:
        print(f"ERROR in format_operation_response_action: {e}")
        if op_type_str == "删除":
            final_answer = "删除操作已执行，但格式化响应时出错。请检查数据以确认删除结果。"
        else:
            final_answer = f"格式化最终响应时出错: {e}"

    return {"final_answer": final_answer} 