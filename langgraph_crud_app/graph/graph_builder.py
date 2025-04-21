# graph_builder.py: 构建 LangGraph 图，定义节点和边。

from langgraph.graph import StateGraph, END
from typing import Dict, Any

# 导入状态定义和节点函数
# 使用绝对导入路径
from langgraph_crud_app.graph.state import GraphState
from langgraph_crud_app.nodes import actions, routers

# --- 占位符节点 (用于连接尚未实现的主流程和错误处理) ---

def main_flow_placeholder_node(state: GraphState) -> Dict[str, Any]:
    """
    主流程入口的占位符节点。
    实际应用中，这里会连接到第一个主流程节点 (例如意图分类)。
    """
    print("---节点: 进入主流程 (占位符)---")
    # 可以选择在这里清除初始化过程中的中间状态
    # return {
    #     "raw_schema_result": None,
    #     "raw_table_names_str": None,
    #     "error_message": None # 清除可能由初始化成功路径产生的非致命错误
    # }
    # 或者，暂时只打印信息并结束
    print(f"当前状态重要信息: Schema={state.get('biaojiegou_save') is not None}, 表名={state.get('table_names')}, 数据示例={state.get('data_sample') is not None}")
    return {"final_answer": "初始化完成，准备进入主流程。"} # 暂时返回一个消息

def error_handling_placeholder_node(state: GraphState) -> Dict[str, Any]:
    """
    错误处理流程的占位符节点。
    实际应用中，这里可以实现更复杂的错误处理逻辑，例如通知用户或尝试恢复。
    """
    print("---节点: 处理错误 (占位符)---")
    error = state.get("error_message", "未知错误")
    print(f"捕获到错误: {error}")
    return {"final_answer": f"处理过程中遇到错误: {error}"} # 直接将错误信息返回给用户

# --- 构建图 ---
def build_graph() -> StateGraph:
    """构建并返回 LangGraph 应用的图实例。"""
    graph = StateGraph(GraphState)

    # --- 添加节点 ---
    # 初始化流程节点
    graph.add_node("route_initialization_node", routers.route_initialization_node)
    graph.add_node("fetch_schema", actions.fetch_schema_action)
    graph.add_node("extract_table_names", actions.extract_table_names_action)
    graph.add_node("process_table_names", actions.process_table_names_action)
    graph.add_node("format_schema", actions.format_schema_action)
    graph.add_node("fetch_sample_data", actions.fetch_sample_data_action)

    # 占位符节点
    graph.add_node("main_flow_entry", main_flow_placeholder_node)
    graph.add_node("handle_init_error", error_handling_placeholder_node)

    # --- 设置入口点 ---
    graph.set_entry_point("route_initialization_node")

    # --- 添加边 ---
    # 初始化路由
    graph.add_conditional_edges(
        "route_initialization_node",
        # Use the dedicated routing logic function
        routers._get_initialization_route,
        {
            "start_initialization": "fetch_schema",
            "continue_to_main_flow": "main_flow_entry", # 直接跳到主流程 (占位符)
            "handle_error": "handle_init_error"       # 进入错误处理 (占位符)
        }
    )

    # 初始化流程顺序边
    graph.add_edge("fetch_schema", "extract_table_names")
    graph.add_edge("extract_table_names", "process_table_names")
    graph.add_edge("process_table_names", "format_schema")
    graph.add_edge("format_schema", "fetch_sample_data")

    # 初始化成功后，进入主流程
    # 注意：这里假设 fetch_sample_data 成功后总是进入主流程
    # 如果 fetch_sample_data 可能产生需要特殊处理的错误，可以在其后添加路由
    graph.add_edge("fetch_sample_data", "main_flow_entry")

    # 错误处理流程的结束点 (或者可以连接到其他恢复逻辑)
    graph.add_edge("handle_init_error", END)
    # 主流程占位符的结束点 (实际会连接到后续节点)
    graph.add_edge("main_flow_entry", END)

    # --- 编译图 --- (通常在 main.py 或应用入口处完成)
    # app = graph.compile()
    # return app
    return graph # 返回未编译的图，以便在 main.py 中编译 