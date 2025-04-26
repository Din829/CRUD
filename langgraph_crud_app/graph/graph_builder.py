# graph_builder.py: 构建 LangGraph 图，定义节点和边。

from langgraph.graph import StateGraph, END
from typing import Dict, Any, Literal

# 导入状态定义和节点函数
from langgraph_crud_app.graph.state import GraphState
# 修改导入: 从新的 actions 文件和 routers 导入
from langgraph_crud_app.nodes import routers # routers 不变
from langgraph_crud_app.nodes import preprocessing_actions, query_actions, flow_control_actions

# --- 占位符节点 (用于连接尚未实现的主流程和错误处理) ---
# 移除旧的 main_flow_placeholder_node 和 error_handling_placeholder_node
# def main_flow_placeholder_node(state: GraphState) -> Dict[str, Any]:
#     ...
# def error_handling_placeholder_node(state: GraphState) -> Dict[str, Any]:
#     ...

# --- 构建图 ---
def build_graph() -> StateGraph:
    """构建并返回 LangGraph 应用的图实例。"""
    graph = StateGraph(GraphState)

    # --- 添加节点 ---
    # 初始化流程节点 (从 preprocessing_actions 导入)
    graph.add_node("route_initialization_node", routers.route_initialization_node)
    graph.add_node("fetch_schema", preprocessing_actions.fetch_schema_action)
    graph.add_node("extract_table_names", preprocessing_actions.extract_table_names_action)
    graph.add_node("process_table_names", preprocessing_actions.process_table_names_action)
    graph.add_node("format_schema", preprocessing_actions.format_schema_action)
    graph.add_node("fetch_sample_data", preprocessing_actions.fetch_sample_data_action)
    # handle_init_error 节点现在需要定义或使用一个实际的错误处理节点
    # 暂时先指向一个简单的占位符或 END
    # graph.add_node("handle_init_error", actions.handle_clarify_query_action) # 复用澄清节点作为初始化错误处理
    # 暂时定义一个简单的初始化错误处理节点
    graph.add_node("handle_init_error", lambda state: {"final_answer": f"初始化错误: {state.get('error_message', '未知错误')}"})

    # 主流程路由节点 (从 routers 导入)
    graph.add_node("classify_main_intent_node", routers.classify_main_intent_node)
    graph.add_node("classify_query_analysis_node", routers.classify_query_analysis_node)
    graph.add_node("route_after_query_execution", routers.route_after_query_execution_node)

    # 主流程控制动作节点 (从 flow_control_actions 导入)
    graph.add_node("handle_reset", flow_control_actions.handle_reset_action)
    graph.add_node("handle_modify_intent", flow_control_actions.handle_modify_intent_action)
    graph.add_node("handle_add_intent", flow_control_actions.handle_add_intent_action)
    graph.add_node("handle_delete_intent", flow_control_actions.handle_delete_intent_action)
    graph.add_node("handle_confirm_other", flow_control_actions.handle_confirm_other_action)

    # 查询/分析 动作节点 (从 query_actions 导入)
    graph.add_node("generate_select_sql", query_actions.generate_select_sql_action)
    graph.add_node("generate_analysis_sql", query_actions.generate_analysis_sql_action)
    graph.add_node("clean_sql", query_actions.clean_sql_action)
    graph.add_node("execute_sql_query", query_actions.execute_sql_query_action)
    graph.add_node("format_query_result", query_actions.format_query_result_action)
    graph.add_node("analyze_analysis_result", query_actions.analyze_analysis_result_action)
    graph.add_node("handle_clarify_query", query_actions.handle_clarify_query_action)
    graph.add_node("handle_clarify_analysis", query_actions.handle_clarify_analysis_action)
    graph.add_node("handle_query_not_found", query_actions.handle_query_not_found_action)
    graph.add_node("handle_analysis_no_data", query_actions.handle_analysis_no_data_action)

    # --- 设置入口点 ---
    graph.set_entry_point("route_initialization_node")

    # --- 添加边 ---
    # 初始化路由 (router 逻辑不变)
    graph.add_conditional_edges(
        "route_initialization_node",
        routers._get_initialization_route,
        {
            "start_initialization": "fetch_schema",
            "continue_to_main_flow": "classify_main_intent_node",
            "handle_error": "handle_init_error"
        }
    )

    # 初始化流程顺序边 (节点名不变)
    graph.add_edge("fetch_schema", "extract_table_names")
    graph.add_edge("extract_table_names", "process_table_names")
    graph.add_edge("process_table_names", "format_schema")
    graph.add_edge("format_schema", "fetch_sample_data")
    graph.add_edge("fetch_sample_data", "classify_main_intent_node")

    # 主意图路由 (router 逻辑和节点名不变)
    graph.add_conditional_edges(
        "classify_main_intent_node",
        routers._route_after_main_intent,
        {
            "classify_query_analysis_node": "classify_query_analysis_node",
            "handle_modify_intent": "handle_modify_intent",
            "handle_add_intent": "handle_add_intent",
            "handle_delete_intent": "handle_delete_intent",
            "handle_reset": "handle_reset",
            "handle_confirm_other": "handle_confirm_other"
        }
    )

    # 查询/分析 子意图路由 (router 逻辑和节点名不变)
    graph.add_conditional_edges(
        "classify_query_analysis_node",
        routers._route_query_or_analysis,
        {
            "query": "generate_select_sql",
            "analysis": "generate_analysis_sql"
        }
    )

    # SQL 生成后直接进行清理
    graph.add_edge("generate_select_sql", "clean_sql")
    graph.add_edge("generate_analysis_sql", "clean_sql")

    # 清理 SQL 后执行查询 (节点名不变)
    graph.add_edge("clean_sql", "execute_sql_query")

    # 执行 SQL 后进行路由判断 (节点名不变)
    graph.add_edge("execute_sql_query", "route_after_query_execution")

    # 根据 SQL 执行结果路由到最终处理或回复节点 (router 逻辑和节点名不变)
    graph.add_conditional_edges(
        "route_after_query_execution",
        routers._route_after_query_execution,
        {
            "format_query_result": "format_query_result",
            "analyze_analysis_result": "analyze_analysis_result",
            "handle_query_not_found": "handle_query_not_found",
            "handle_analysis_no_data": "handle_analysis_no_data",
            "handle_clarify_query": "handle_clarify_query",
            "handle_clarify_analysis": "handle_clarify_analysis"
        }
    )

    # 各分支结束点 (节点名不变)
    graph.add_edge("handle_init_error", END)
    graph.add_edge("handle_reset", END)
    graph.add_edge("handle_modify_intent", END)
    graph.add_edge("handle_add_intent", END)
    graph.add_edge("handle_delete_intent", END)
    graph.add_edge("handle_confirm_other", END)
    graph.add_edge("handle_clarify_query", END)
    graph.add_edge("handle_clarify_analysis", END)
    graph.add_edge("handle_query_not_found", END)
    graph.add_edge("handle_analysis_no_data", END)
    graph.add_edge("format_query_result", END)
    graph.add_edge("analyze_analysis_result", END)

    return graph # 返回未编译的图

# --- 编译图 --- (通常在 main.py 或应用入口处完成)
# app = graph.compile()
# return app 