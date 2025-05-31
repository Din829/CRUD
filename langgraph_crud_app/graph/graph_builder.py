# graph_builder.py: 构建 LangGraph 图，定义节点和边。

from langgraph.graph import StateGraph, END
from typing import Dict, Any, Literal

# 导入状态定义和节点函数
from langgraph_crud_app.graph.state import GraphState
# 修改导入: 从 nodes 下的 actions 和 routers 子目录导入
from langgraph_crud_app.nodes.routers import initialization_router, main_router, query_analysis_router, confirmation_router
# 从 nodes.actions 导入需要的 *函数* 而不是模块
from langgraph_crud_app.nodes.actions import (
    # Preprocessing
    fetch_schema_action, 
    extract_table_names_action,
    process_table_names_action,
    format_schema_action,
    fetch_sample_data_action,
    # Query/Analysis
    generate_select_sql_action,
    generate_analysis_sql_action,
    clean_sql_action,
    execute_sql_query_action,
    handle_query_not_found_action,
    handle_analysis_no_data_action,
    handle_clarify_query_action,
    handle_clarify_analysis_action,
    format_query_result_action,
    analyze_analysis_result_action,
    # Modify
    generate_modify_context_sql_action,
    execute_modify_context_sql_action,
    parse_modify_request_action,
    validate_and_store_modification_action,
    handle_modify_error_action,
    provide_modify_feedback_action,
    # Flow Control / Confirmation
    handle_reset_action,
    stage_modify_action,
    stage_add_action,
    stage_combined_action,
    handle_nothing_to_stage_action,
    handle_invalid_save_state_action,
    cancel_save_action,
    execute_operation_action,
    reset_after_operation_action,
    format_operation_response_action,
    handle_add_intent_action,
    handle_delete_intent_action,
    # Composite
    parse_combined_request_action,
    format_combined_preview_action
)
# 🎯 UI/UX改进：删除操作不再需要独立的暂存节点
# from langgraph_crud_app.nodes.actions.flow_control_actions import stage_delete_action  # 已移除
# 单独导入 add_actions 中的函数
from langgraph_crud_app.nodes.actions.add_actions import (
    parse_add_request_action,
    process_add_llm_output_action,
    process_placeholders_action,
    format_add_preview_action,
    provide_add_feedback_action,
    handle_add_error_action,
    finalize_add_response,
)

# 新增：从 composite_actions 导入
from langgraph_crud_app.nodes.actions.composite_actions import (
    parse_combined_request_action,
    format_combined_preview_action,
    process_composite_placeholders_action
)

# 新增：从 delete_actions 导入
from langgraph_crud_app.nodes.actions.delete_actions import (
    generate_delete_preview_sql_action,
    clean_delete_sql_action,
    execute_delete_preview_sql_action,
    format_delete_preview_action,
    provide_delete_feedback_action,
    handle_delete_error_action,
    finalize_delete_response,
)

# --- 内部路由逻辑函数 ---
def _route_after_validation(state: GraphState) -> Literal["handle_modify_error_action", "provide_modify_feedback_action"]:
    """根据验证结果路由到错误处理或用户反馈。"""
    if state.get("error_message"):
        return "handle_modify_error_action"
    else:
        return "provide_modify_feedback_action"

def _route_after_context_sql_generation(state: GraphState) -> Literal["execute_modify_context_sql_action", "handle_modify_error_action"]:
    """根据上下文 SQL 生成结果路由。"""
    if state.get("error_message") or not state.get("modify_context_sql"):
        # 如果生成 SQL 出错，或 LLM 返回空 (此时 final_answer 已被设置)
        return "handle_modify_error_action" # 或者直接 END ? 如果有 final_answer 可能应该结束
    else:
        return "execute_modify_context_sql_action"

def _route_after_context_sql_execution(state: GraphState) -> Literal["parse_modify_request_action", "handle_modify_error_action"]:
    """根据上下文 SQL 执行结果路由。"""
    if state.get("error_message"):
        return "handle_modify_error_action"
    else:
        # 即使 context_result 为空或 '[]'，也应继续解析，LLM 需要此信息
        return "parse_modify_request_action"

def _route_add_flow_on_error(state: GraphState) -> Literal["handle_add_error", "continue"]:
    """检查新增流程步骤中的错误状态。"""
    print("--- Debug: Routing Add Flow - State received by router ---")
    parse_error = state.get("add_parse_error")
    process_error = state.get("add_error_message")
    if parse_error or process_error:
        print(f"--- Routing Add Flow to Error Handler. ParseError: {parse_error}, ProcessError: {process_error} ---")
        return "handle_add_error"
    else:
        # 检查 temp_add_llm_data 是否存在，如果不存在也应报错
        if state.get("temp_add_llm_data") is None and not parse_error:
             print("--- Routing Add Flow to Error Handler. temp_add_llm_data is None but no parse_error reported. ---")
             return "handle_add_error"
        print("--- Routing Add Flow to Continue ---")
        return "continue"

# 新增：删除流程错误路由
def _route_delete_flow_on_error(state: GraphState) -> Literal["handle_delete_error_action", "continue"]:
    """检查删除流程步骤中的错误状态或 LLM 提示。"""
    print("--- Debug: Routing Delete Flow - State received by router ---")
    error_message = state.get("delete_error_message")
    # 检查 generate_sql 步骤是否直接返回了 final_answer (表示 LLM 返回了提示)
    final_answer_at_start = state.get("final_answer") 
    # 检查 SQL 是否为空，这也是一种错误或停止信号
    preview_sql = state.get("delete_preview_sql")

    if error_message:
        print(f"--- Routing Delete Flow to Error Handler. Error: {error_message} ---")
        return "handle_delete_error_action"
    # 如果 generate_sql 设置了 final_answer，说明 LLM 没生成 SQL，流程应停止
    elif final_answer_at_start:
        print(f"--- Routing Delete Flow to End (via final_answer): {final_answer_at_start} ---")
        # 这里直接路由到 handle_delete_error，让它设置 error_flag 并结束
        # 或者可以创建一个专门的"停止"节点
        return "handle_delete_error_action"
    elif preview_sql is None and not error_message and not final_answer_at_start:
        # SQL 为空，且没有明确的错误或提示，也视为错误
         print("--- Routing Delete Flow to Error Handler. delete_preview_sql is None without reported error. ---")
         return "handle_delete_error_action"
    else:
        print("--- Routing Delete Flow to Continue ---")
        return "continue"

# 新增：初始化流程中每一步后的错误检查路由
def _route_init_step_on_error(state: GraphState) -> Literal["handle_init_error", "continue"]:
    """如果当前状态中存在 error_message, 则路由到错误处理，否则继续。"""
    if state.get("error_message"):
        print(f"--- 初始化步骤中检测到错误: {state.get('error_message')}, 路由到 handle_init_error ---")
        return "handle_init_error"
    return "continue"

def _route_after_sql_generation(state: GraphState) -> Literal["continue_to_clean_sql", "clarify_query", "clarify_analysis"]:
    """
    在 SQL 生成后进行路由。
    如果生成的是澄清请求，则路由到相应的澄清处理节点。
    否则，继续到 SQL 清理节点。
    """
    sql_generated_value = state.get("sql_query_generated") # 直接获取原始值
    query_analysis_intent = state.get("query_analysis_intent", "query") # 默认为 query

    # 首先检查 sql_generated_value 是否为字符串并且是 CLARIFY:
    if isinstance(sql_generated_value, str) and sql_generated_value.strip().upper().startswith("CLARIFY:"):
        print(f"---路由逻辑: _route_after_sql_generation - 检测到澄清请求: {sql_generated_value[:100]}... ---")
        if query_analysis_intent == "analysis":
            print("---路由决策: 返回 'clarify_analysis' (因为是澄清且意图是 analysis)---")
            return "clarify_analysis"
        else: # 默认为 query 或其他情况
            print("---路由决策: 返回 'clarify_query' (因为是澄清且意图是 query/default)---")
            return "clarify_query"
    # 其次，检查 sql_generated_value 是否是一个非空字符串 (表示正常的SQL)
    elif isinstance(sql_generated_value, str) and sql_generated_value.strip(): # 确保它不只是空字符串
        print(f"---路由逻辑: _route_after_sql_generation - SQL生成正常，继续清理: {sql_generated_value[:100]}... ---")
        print("---路由决策: 返回 'continue_to_clean_sql'---")
        return "continue_to_clean_sql"
    else:
        # 如果 sql_generated_value 是 None, 空字符串, 或者其他非CLARIFY、非有效SQL的情况
        # 打印时进行安全处理
        print(f"---路由逻辑: _route_after_sql_generation - SQL生成值不是澄清，也不是有效SQL字符串 (可能是None或错误指示): '{str(sql_generated_value)[:200]}...' ---")
        print("---路由决策: 返回 'continue_to_clean_sql' (后续节点如 clean_sql 应能处理 None/空值)---")
        return "continue_to_clean_sql"

# --- 构建图 ---
def build_graph() -> StateGraph:
    """构建并返回 LangGraph 应用的图实例。"""
    graph = StateGraph(GraphState)

    # --- 添加节点 ---
    # 初始化流程节点
    graph.add_node("route_initialization_node", initialization_router.route_initialization_node) # 图入口，检查是否需要初始化
    graph.add_node("fetch_schema", fetch_schema_action) # 调用 API 获取 Schema
    graph.add_node("extract_table_names", extract_table_names_action) # LLM 提取表名
    graph.add_node("process_table_names", process_table_names_action) # 清理表名列表
    graph.add_node("format_schema", format_schema_action) # LLM 格式化 Schema
    graph.add_node("fetch_sample_data", fetch_sample_data_action) # 调用 API 获取数据示例
    graph.add_node("handle_init_error", lambda state: {"final_answer": f"初始化错误: {state.get('error_message', '未知错误')}"}) # 处理初始化错误

    # 主流程路由节点
    graph.add_node("classify_main_intent_node", main_router.classify_main_intent_node) # LLM 分类用户主意图

    # 查询/分析 路由节点
    graph.add_node("classify_query_analysis_node", query_analysis_router.classify_query_analysis_node) # LLM 分类查询/分析子意图
    graph.add_node("route_after_query_execution", query_analysis_router.route_after_query_execution_node) # SQL 执行后路由决策点

    # 主流程控制动作节点 (从 actions.flow_control_actions 导入)
    graph.add_node("handle_reset", handle_reset_action) # 处理重置意图
    graph.add_node("handle_add_intent", handle_add_intent_action) # (占位符/未使用?)
    graph.add_node("handle_delete_intent", handle_delete_intent_action) # (占位符/未使用?)

    # 查询/分析 动作节点
    graph.add_node("generate_select_sql", generate_select_sql_action) # LLM 生成 SELECT SQL
    graph.add_node("generate_analysis_sql", generate_analysis_sql_action) # LLM 生成分析 SQL
    graph.add_node("clean_sql", clean_sql_action) # 清理 SQL 语句
    graph.add_node("execute_sql_query", execute_sql_query_action) # 调用 API 执行 SQL 查询
    graph.add_node("format_query_result", format_query_result_action) # LLM 格式化查询结果
    graph.add_node("analyze_analysis_result", analyze_analysis_result_action) # LLM 分析结果
    graph.add_node("handle_clarify_query", handle_clarify_query_action) # 处理查询需澄清
    graph.add_node("handle_clarify_analysis", handle_clarify_analysis_action) # 处理分析需澄清
    graph.add_node("handle_query_not_found", handle_query_not_found_action) # 处理查询无结果
    graph.add_node("handle_analysis_no_data", handle_analysis_no_data_action) # 处理分析无数据

    # 确认流程路由节点
    graph.add_node("route_confirmation_entry", confirmation_router.route_confirmation_entry) # 确认流程入口
    graph.add_node("stage_operation_node", confirmation_router.stage_operation_node) # 路由到具体暂存动作
    graph.add_node("check_staged_operation_node", confirmation_router.check_staged_operation_node) # 检查已暂存的操作
    graph.add_node("ask_confirm_modify_node", confirmation_router.ask_confirm_modify_node) # 询问用户最终确认

    # 确认流程动作节点
    graph.add_node("stage_modify_action", stage_modify_action) # 暂存修改操作
    graph.add_node("stage_add_action", stage_add_action) # 暂存新增操作
    graph.add_node("handle_nothing_to_stage", handle_nothing_to_stage_action) # 处理无操作可暂存
    graph.add_node("handle_invalid_save_state", handle_invalid_save_state_action) # 处理无效暂存状态
    graph.add_node("cancel_save_action", cancel_save_action) # 用户取消保存操作
    graph.add_node("execute_operation_action", execute_operation_action) # 调用 API 执行操作 (增/改/复合/删)
    graph.add_node("reset_after_operation_action", reset_after_operation_action) # 操作后重置状态
    graph.add_node("format_operation_response_action", format_operation_response_action) # LLM 格式化操作结果

    # 新增：修改流程动作节点 (从 actions.modify_actions 导入)
    graph.add_node("parse_modify_request_action", parse_modify_request_action) # LLM 解析修改请求 (含上下文)
    graph.add_node("validate_and_store_modification_action", validate_and_store_modification_action) # 验证并存储解析结果
    graph.add_node("handle_modify_error_action", handle_modify_error_action) # 处理修改流程错误
    graph.add_node("provide_modify_feedback_action", provide_modify_feedback_action) # 提供修改预览给用户

    # 新增：修改流程上下文查询节点
    graph.add_node("generate_modify_context_sql_action", generate_modify_context_sql_action) # LLM 生成获取修改上下文的 SQL
    graph.add_node("execute_modify_context_sql_action", execute_modify_context_sql_action) # 执行上下文 SQL

    # 新增：添加流程动作节点
    graph.add_node("parse_add_request", parse_add_request_action) # LLM 解析新增请求
    graph.add_node("process_add_llm_output", process_add_llm_output_action) # 清理/结构化新增 LLM 输出
    graph.add_node("process_placeholders", process_placeholders_action) # 处理新增流程占位符 (db/random)
    graph.add_node("format_add_preview", format_add_preview_action) # LLM 格式化新增预览
    graph.add_node("provide_add_feedback", provide_add_feedback_action) # 提供新增预览给用户
    graph.add_node("handle_add_error", handle_add_error_action) # 处理新增流程错误

    # 新增：添加 finalize_add_response 节点
    graph.add_node("finalize_add_response", finalize_add_response) # (占位符/确保合并状态?)

    # 新增：复合操作节点
    graph.add_node("parse_combined_request", parse_combined_request_action) # LLM 解析复合请求
    graph.add_node("format_combined_preview", format_combined_preview_action) # LLM 格式化复合预览
    graph.add_node("stage_combined_action", stage_combined_action) # 暂存复合操作

    # 新增：复合占位符处理节点
    graph.add_node("process_composite_placeholders", process_composite_placeholders_action) # 处理复合流程占位符 (db/random)

    # 新增：删除流程节点
    graph.add_node("generate_delete_preview_sql_action", generate_delete_preview_sql_action)
    graph.add_node("clean_delete_sql_action", clean_delete_sql_action)
    graph.add_node("execute_delete_preview_sql_action", execute_delete_preview_sql_action)
    graph.add_node("format_delete_preview_action", format_delete_preview_action)
    graph.add_node("provide_delete_feedback_action", provide_delete_feedback_action)
    graph.add_node("handle_delete_error_action", handle_delete_error_action)
    graph.add_node("finalize_delete_response", finalize_delete_response)

    # 🎯 UI/UX改进：删除操作不再需要独立的暂存节点，已在预览阶段直接设置暂存状态
    # graph.add_node("stage_delete_action", stage_delete_action)  # 已移除

    # --- 设置入口点 ---
    graph.set_entry_point("route_initialization_node")

    # --- 添加边 ---
    # 初始化路由
    graph.add_conditional_edges(
        "route_initialization_node",
        initialization_router._get_initialization_route,
        {
            "start_initialization": "fetch_schema",
            "continue_to_main_flow": "classify_main_intent_node",
            "handle_error": "handle_init_error"
        }
    )

    # 初始化流程顺序边 - 修改为条件边以处理每一步的错误
    graph.add_conditional_edges(
        "fetch_schema",
        _route_init_step_on_error,
        {
            "continue": "extract_table_names",
            "handle_init_error": "handle_init_error"
        }
    )
    graph.add_conditional_edges(
        "extract_table_names",
        _route_init_step_on_error,
        {
            "continue": "process_table_names",
            "handle_init_error": "handle_init_error"
        }
    )
    graph.add_conditional_edges(
        "process_table_names",
        _route_init_step_on_error,
        {
            "continue": "format_schema",
            "handle_init_error": "handle_init_error"
        }
    )
    graph.add_conditional_edges(
        "format_schema",
        _route_init_step_on_error,
        {
            "continue": "fetch_sample_data",
            "handle_init_error": "handle_init_error"
        }
    )
    graph.add_conditional_edges(
        "fetch_sample_data",
        _route_init_step_on_error, # 检查 fetch_sample_data 自身执行期间是否出错
        {
            "continue": "classify_main_intent_node", # 成功则进入主流程
            "handle_init_error": "handle_init_error"
        }
    )

    # 主意图路由 (修改 modify 指向)
    graph.add_conditional_edges(
        "classify_main_intent_node",
        main_router._route_after_main_intent,
        {
            "continue_to_query_analysis": "classify_query_analysis_node",
            "continue_to_modify": "generate_modify_context_sql_action",
            "start_add_flow": "parse_add_request",
            "start_composite_flow": "parse_combined_request",
            "start_delete_flow": "generate_delete_preview_sql_action",
            "reset_flow": "handle_reset",
            "continue_to_confirmation": "route_confirmation_entry"
        }
    )

    # 修改流程 - 上下文查询部分的边
    graph.add_conditional_edges(
        "generate_modify_context_sql_action",
        _route_after_context_sql_generation,
        {
            "execute_modify_context_sql_action": "execute_modify_context_sql_action",
            "handle_modify_error_action": "handle_modify_error_action" 
            # 如果 generate_modify_context_sql_action 设置了 final_answer，可能需要直接 END
        }
    )
    # 修改流程 - 上下文查询执行部分的边
    graph.add_conditional_edges(
        "execute_modify_context_sql_action",
        _route_after_context_sql_execution,
        {
            "parse_modify_request_action": "parse_modify_request_action",
            "handle_modify_error_action": "handle_modify_error_action"
        }
    )

    # 修改流程 - 解析、验证、反馈部分的边 (保持不变)
    graph.add_edge("parse_modify_request_action", "validate_and_store_modification_action")

    # 修改流程 - 验证、反馈路由
    graph.add_conditional_edges(
        "validate_and_store_modification_action",
        _route_after_validation, # 这个内部路由函数保持不变
        {
            "handle_modify_error_action": "handle_modify_error_action",
            "provide_modify_feedback_action": "provide_modify_feedback_action"
        }
    )

    # 确认流程路由
    graph.add_conditional_edges(
        "route_confirmation_entry",
        confirmation_router._route_confirmation_entry_logic,
        {
            "check_staged_operation_node": "check_staged_operation_node",
            "stage_operation_node": "stage_operation_node" 
        }
    )
    # 确认流程 - 操作阶段路由 
    graph.add_conditional_edges(
        "stage_operation_node",
        confirmation_router._stage_operation_logic,
        {
            "stage_modify_action": "stage_modify_action",
            "stage_add_action": "stage_add_action", # 新增路由
            "stage_combined_action": "stage_combined_action", # 新增：复合暂存路由
            # 🎯 UI/UX改进：删除操作已在预览阶段直接设置暂存，无需再次暂存
            "handle_nothing_to_stage": "handle_nothing_to_stage"
        }
    )
    # 确认流程 - 检查已暂存操作路由 (使用更新后的逻辑)
    graph.add_conditional_edges(
        "check_staged_operation_node",
        confirmation_router._check_staged_operation_logic,
        {
            "ask_confirm_modify_node": "ask_confirm_modify_node",
            "handle_invalid_save_state": "handle_invalid_save_state"
        }
    )
    # 确认流程 - 询问确认路由 (使用更新后的逻辑和目标节点)
    graph.add_conditional_edges(
        "ask_confirm_modify_node",
        confirmation_router._ask_confirm_modify_logic,
        {
            "execute_operation_action": "execute_operation_action", # 指向重命名后的执行节点
            "cancel_save_action": "cancel_save_action"
        }
    )

    # 确认流程动作序列 (使用重命名后的节点)
    graph.add_edge("execute_operation_action", "reset_after_operation_action")
    graph.add_edge("reset_after_operation_action", "format_operation_response_action")
    # 新增：暂存动作完成后结束当前轮，等待用户确认
    graph.add_edge("stage_modify_action", END)
    graph.add_edge("stage_add_action", END)
    graph.add_edge("stage_combined_action", END)
    # 🎯 UI/UX改进：删除操作无需独立暂存边，已在预览阶段处理
    # graph.add_edge("stage_delete_action", END)  # 已移除
    graph.add_edge("handle_nothing_to_stage", END)

    # 查询/分析 子意图路由
    graph.add_conditional_edges(
        "classify_query_analysis_node",
        query_analysis_router._route_query_or_analysis,
        {
            "query": "generate_select_sql",       # 确保与 add_node 一致
            "analysis": "generate_analysis_sql" # 确保与 add_node 一致
        }
    )

    # 查询/分析 - SQL 生成后 (使用新的条件路由)
    graph.add_conditional_edges(
        "generate_select_sql", # 确保与 add_node 一致
        _route_after_sql_generation,
        {
            "clarify_query": "handle_clarify_query", # 确保与 add_node 一致
            "clarify_analysis": "handle_clarify_analysis", # 确保与 add_node 一致
            "continue_to_clean_sql": "clean_sql" # 确保与 add_node 一致
        }
    )
    graph.add_conditional_edges(
        "generate_analysis_sql", # 确保与 add_node 一致
        _route_after_sql_generation,
        {
            "clarify_query": "handle_clarify_query", # 确保与 add_node 一致
            "clarify_analysis": "handle_clarify_analysis", # 确保与 add_node 一致
            "continue_to_clean_sql": "clean_sql" # 确保与 add_node 一致
        }
    )

    # 查询/分析 - SQL 清理后
    graph.add_edge("clean_sql", "execute_sql_query") # 确保与 add_node 一致

    # 执行 SQL 后进行路由判断
    graph.add_edge("execute_sql_query", "route_after_query_execution") # 确保与 add_node 一致

    # 根据 SQL 执行结果路由到最终处理或回复节点
    graph.add_conditional_edges(
        "route_after_query_execution",
        query_analysis_router._route_after_query_execution,
        {
            "format_query_result": "format_query_result", # 确保与 add_node 一致
            "analyze_analysis_result": "analyze_analysis_result", # 确保与 add_node 一致
            "handle_query_not_found": "handle_query_not_found", # 确保与 add_node 一致
            "handle_analysis_no_data": "handle_analysis_no_data", # 确保与 add_node 一致
            "handle_clarify_query": "handle_clarify_query", # 确保与 add_node 一致
            "handle_clarify_analysis": "handle_clarify_analysis" # 确保与 add_node 一致
        }
    )

    # 新增流程 - 主要顺序和错误处理边
    graph.add_conditional_edges(
        "parse_add_request",
        _route_add_flow_on_error,
        {
            "handle_add_error": "handle_add_error",
            "continue": "process_add_llm_output"
        }
    )
    # ---- 恢复条件路由 ----
    graph.add_conditional_edges(
        "process_add_llm_output",
        _route_add_flow_on_error,
        {
            "handle_add_error": "handle_add_error",
            "continue": "process_placeholders"
        }
    )
    # ---- END 恢复 ----
    graph.add_conditional_edges(
        "process_placeholders",
        _route_add_flow_on_error,
        {
            "handle_add_error": "handle_add_error",
            "continue": "format_add_preview"
        }
    )
    graph.add_conditional_edges(
        "format_add_preview",
        _route_add_flow_on_error, # format_add_preview 也会设置 add_error_message
        {
            "handle_add_error": "handle_add_error",
            "continue": "provide_add_feedback"
        }
    )

    # 新增流程 - 反馈后通过 finalize 节点结束
    # 移除: graph.add_edge("provide_add_feedback", END)
    graph.add_edge("provide_add_feedback", "finalize_add_response")
    graph.add_edge("finalize_add_response", END)

    # 新增流程 - 错误处理后结束
    graph.add_edge("handle_add_error", END)

    # 新增：复合流程边
    # 解析后 -> 处理占位符 -> 格式化预览 -> 确认入口
    graph.add_edge("parse_combined_request", "process_composite_placeholders")
    graph.add_edge("process_composite_placeholders", "format_combined_preview")
    graph.add_edge("format_combined_preview", "route_confirmation_entry")

    # 确认流程动作序列 (使用重命名后的节点)
    graph.add_edge("execute_operation_action", "reset_after_operation_action")

    # 新增：删除流程边
    graph.add_conditional_edges(
        "generate_delete_preview_sql_action",
        _route_delete_flow_on_error, # 使用新的错误路由逻辑
        {
            "continue": "clean_delete_sql_action",
            "handle_delete_error_action": "handle_delete_error_action"
        }
    )
    graph.add_conditional_edges(
        "clean_delete_sql_action",
        _route_delete_flow_on_error, # 复用错误检查
        {
            "continue": "execute_delete_preview_sql_action",
            "handle_delete_error_action": "handle_delete_error_action"
        }
    )
    graph.add_conditional_edges(
        "execute_delete_preview_sql_action",
        _route_delete_flow_on_error, # 复用错误检查
        {
            "continue": "format_delete_preview_action",
            "handle_delete_error_action": "handle_delete_error_action"
        }
    )
    graph.add_conditional_edges(
        "format_delete_preview_action",
        _route_delete_flow_on_error, # 复用错误检查
        {
            "continue": "provide_delete_feedback_action",
            "handle_delete_error_action": "handle_delete_error_action"
        }
    )
    graph.add_edge("provide_delete_feedback_action", "finalize_delete_response")
    graph.add_edge("finalize_delete_response", END)
    graph.add_edge("handle_delete_error_action", END) # 错误路径结束

    # 通用结束和重置边
    graph.add_edge("handle_init_error", END)
    graph.add_edge("handle_reset", END) # 重置后结束当前轮次
    graph.add_edge("handle_nothing_to_stage", END)
    graph.add_edge("handle_invalid_save_state", END)
    graph.add_edge("cancel_save_action", END)
    graph.add_edge("format_operation_response_action", END) # API 操作完成后结束
    graph.add_edge("handle_modify_error_action", END) # 修改流程错误处理后结束
    # 查询分析流程的结束点
    graph.add_edge("format_query_result", END)
    graph.add_edge("analyze_analysis_result", END)
    graph.add_edge("handle_clarify_query", END)
    graph.add_edge("handle_clarify_analysis", END)
    graph.add_edge("handle_query_not_found", END)
    graph.add_edge("handle_analysis_no_data", END)

    return graph

# --- 编译图 --- (通常在 main.py 或应用入口处完成)
# app = graph.compile()
# return app 