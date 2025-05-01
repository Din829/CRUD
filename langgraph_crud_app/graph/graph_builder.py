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
    handle_nothing_to_stage_action,
    handle_invalid_save_state_action,
    cancel_save_action,
    execute_operation_action,
    reset_after_operation_action,
    format_operation_response_action,
    handle_add_intent_action,
    handle_delete_intent_action,
)
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
    """检查新增流程步骤中的错误状态."""
    # --- DEBUG: 打印进入路由函数时的状态 (使用新键名) --- 
    print(f"--- Debug: Routing Add Flow - State received by router ---")
    # --- 新增：打印完整状态 --- 
    print(f"路由函数接收到的完整状态: {state}") 
    # --- END 新增 ---
    print(f"    temp_add_llm_data: {state.get('temp_add_llm_data')}") # 更新键名
    print(f"    add_parse_error: {state.get('add_parse_error')}")
    print(f"    add_error_message: {state.get('add_error_message')}")
    # --- END DEBUG ---
    
    parse_error = state.get("add_parse_error")
    process_error = state.get("add_error_message")
    if parse_error or process_error:
        print(f"--- Routing Add Flow to Error Handler. ParseError: {parse_error}, ProcessError: {process_error} ---")
        return "handle_add_error"
    else:
        return "continue"

# --- 构建图 ---
def build_graph() -> StateGraph:
    """构建并返回 LangGraph 应用的图实例。"""
    graph = StateGraph(GraphState)

    # --- 添加节点 ---
    # 初始化流程节点
    graph.add_node("route_initialization_node", initialization_router.route_initialization_node)
    graph.add_node("fetch_schema", fetch_schema_action)
    graph.add_node("extract_table_names", extract_table_names_action)
    graph.add_node("process_table_names", process_table_names_action)
    graph.add_node("format_schema", format_schema_action)
    graph.add_node("fetch_sample_data", fetch_sample_data_action)
    graph.add_node("handle_init_error", lambda state: {"final_answer": f"初始化错误: {state.get('error_message', '未知错误')}"})

    # 主流程路由节点
    graph.add_node("classify_main_intent_node", main_router.classify_main_intent_node)

    # 查询/分析 路由节点
    graph.add_node("classify_query_analysis_node", query_analysis_router.classify_query_analysis_node)
    graph.add_node("route_after_query_execution", query_analysis_router.route_after_query_execution_node)

    # 主流程控制动作节点 (从 actions.flow_control_actions 导入)
    graph.add_node("handle_reset", handle_reset_action)
    graph.add_node("handle_add_intent", handle_add_intent_action)
    graph.add_node("handle_delete_intent", handle_delete_intent_action)

    # 查询/分析 动作节点
    graph.add_node("generate_select_sql", generate_select_sql_action)
    graph.add_node("generate_analysis_sql", generate_analysis_sql_action)
    graph.add_node("clean_sql", clean_sql_action)
    graph.add_node("execute_sql_query", execute_sql_query_action)
    graph.add_node("format_query_result", format_query_result_action)
    graph.add_node("analyze_analysis_result", analyze_analysis_result_action)
    graph.add_node("handle_clarify_query", handle_clarify_query_action)
    graph.add_node("handle_clarify_analysis", handle_clarify_analysis_action)
    graph.add_node("handle_query_not_found", handle_query_not_found_action)
    graph.add_node("handle_analysis_no_data", handle_analysis_no_data_action)

    # 确认流程路由节点
    graph.add_node("route_confirmation_entry", confirmation_router.route_confirmation_entry)
    graph.add_node("stage_operation_node", confirmation_router.stage_operation_node)
    graph.add_node("check_staged_operation_node", confirmation_router.check_staged_operation_node)
    graph.add_node("ask_confirm_modify_node", confirmation_router.ask_confirm_modify_node)

    # 确认流程动作节点
    graph.add_node("stage_modify_action", stage_modify_action)
    graph.add_node("stage_add_action", stage_add_action)
    graph.add_node("handle_nothing_to_stage", handle_nothing_to_stage_action)
    graph.add_node("handle_invalid_save_state", handle_invalid_save_state_action)
    graph.add_node("cancel_save_action", cancel_save_action)
    graph.add_node("execute_operation_action", execute_operation_action)
    graph.add_node("reset_after_operation_action", reset_after_operation_action)
    graph.add_node("format_operation_response_action", format_operation_response_action)

    # 新增：修改流程动作节点 (从 actions.modify_actions 导入)
    graph.add_node("parse_modify_request_action", parse_modify_request_action)
    graph.add_node("validate_and_store_modification_action", validate_and_store_modification_action)
    graph.add_node("handle_modify_error_action", handle_modify_error_action)
    graph.add_node("provide_modify_feedback_action", provide_modify_feedback_action)

    # 新增：修改流程上下文查询节点
    graph.add_node("generate_modify_context_sql_action", generate_modify_context_sql_action)
    graph.add_node("execute_modify_context_sql_action", execute_modify_context_sql_action)

    # 新增：添加流程动作节点
    graph.add_node("parse_add_request", parse_add_request_action)
    graph.add_node("process_add_llm_output", process_add_llm_output_action)
    graph.add_node("process_placeholders", process_placeholders_action)
    graph.add_node("format_add_preview", format_add_preview_action)
    graph.add_node("provide_add_feedback", provide_add_feedback_action)
    graph.add_node("handle_add_error", handle_add_error_action)

    # 新增：添加 finalize_add_response 节点
    graph.add_node("finalize_add_response", finalize_add_response)

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

    # 初始化流程顺序边
    graph.add_edge("fetch_schema", "extract_table_names")
    graph.add_edge("extract_table_names", "process_table_names")
    graph.add_edge("process_table_names", "format_schema")
    graph.add_edge("format_schema", "fetch_sample_data")
    graph.add_edge("fetch_sample_data", "classify_main_intent_node")

    # 主意图路由 (修改 modify 指向)
    graph.add_conditional_edges(
        "classify_main_intent_node",
        main_router._route_after_main_intent,
        {
            "continue_to_query_analysis": "classify_query_analysis_node",
            "continue_to_modify": "generate_modify_context_sql_action",
            "start_add_flow": "parse_add_request",
            "start_delete_flow": END, # 指向删除占位符或未来实现的节点
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
    # 确认流程 - 操作阶段路由 (添加 stage_add_action)
    graph.add_conditional_edges(
        "stage_operation_node",
        confirmation_router._stage_operation_logic,
        {
            "stage_modify_action": "stage_modify_action",
            "stage_add_action": "stage_add_action", # 新增路由
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

    # 查询/分析 子意图路由
    graph.add_conditional_edges(
        "classify_query_analysis_node",
        query_analysis_router._route_query_or_analysis,
        {
            "query": "generate_select_sql",
            "analysis": "generate_analysis_sql"
        }
    )

    # SQL 生成后直接进行清理
    graph.add_edge("generate_select_sql", "clean_sql")
    graph.add_edge("generate_analysis_sql", "clean_sql")

    # 清理 SQL 后执行查询
    graph.add_edge("clean_sql", "execute_sql_query")

    # 执行 SQL 后进行路由判断
    graph.add_edge("execute_sql_query", "route_after_query_execution")

    # 根据 SQL 执行结果路由到最终处理或回复节点
    graph.add_conditional_edges(
        "route_after_query_execution",
        query_analysis_router._route_after_query_execution,
        {
            "format_query_result": "format_query_result",
            "analyze_analysis_result": "analyze_analysis_result",
            "handle_query_not_found": "handle_query_not_found",
            "handle_analysis_no_data": "handle_analysis_no_data",
            "handle_clarify_query": "handle_clarify_query",
            "handle_clarify_analysis": "handle_clarify_analysis"
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

    # 确认流程路由 (保持不变，但确认 stage_add_action 边存在)
    # ... (确认流程的边保持不变)

    # 查询/分析流程边 (保持不变)
    # ... (查询/分析流程的边保持不变)

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