# routers.py: 包含负责条件路由和逻辑流控制的 LangGraph 节点函数。 

from typing import Literal, Dict, Any

# 导入状态定义和 LLM 服务
from langgraph_crud_app.graph.state import GraphState
from langgraph_crud_app.services import llm_query_service, data_processor # 只需导入查询服务和 data_processor

# --- 初始化流程路由逻辑 ---

def _get_initialization_route(state: GraphState) -> Literal["start_initialization", "continue_to_main_flow", "handle_error"]:
    """
    路由逻辑：检查必要的初始化数据是否已存在于状态中。
    对应 Dify 条件分支节点: '1743973729940'

    Args:
        state: 当前图状态。

    Returns:
        一个字符串，指示下一个要执行的节点。
    """
    error_message = state.get("error_message")
    if error_message:
        return "handle_error"

    biaojiegou_save = state.get("biaojiegou_save")
    table_names = state.get("table_names")
    data_sample = state.get("data_sample")

    if biaojiegou_save and biaojiegou_save != "{}" and table_names and data_sample and data_sample != "{}":
        return "continue_to_main_flow"
    else:
        return "start_initialization"

def route_initialization_node(state: GraphState) -> Dict[str, Any]:
    """
    路由节点：打印状态检查信息，本身不执行路由，仅返回空状态更新。
    路由逻辑由 _get_initialization_route 在条件边中处理。
    """
    print("---路由节点: 检查初始化状态 (打印信息)---")
    error_message = state.get("error_message")
    if error_message:
        print(f"检测到错误，将路由到错误处理: {error_message}")
    else:
        biaojiegou_save = state.get("biaojiegou_save")
        table_names = state.get("table_names")
        data_sample = state.get("data_sample")
        if biaojiegou_save and biaojiegou_save != "{}" and table_names and data_sample and data_sample != "{}":
            print("所有初始化数据已存在，将继续主流程。")
        else:
            missing = []
            if not (biaojiegou_save and biaojiegou_save != "{}"):
                missing.append("Schema")
            if not table_names:
                missing.append("表名")
            if not (data_sample and data_sample != "{}"):
                missing.append("数据示例")
            print(f"缺少初始化数据: {', '.join(missing)}。将开始初始化流程。")

    return {}

# --- 主意图路由 ---

def classify_main_intent_node(state: GraphState) -> Dict[str, Any]:
    """
    路由节点：调用 LLM 服务对用户查询进行主意图分类。
    """
    print("---路由节点: 主意图分类---")
    query = state.get("query", "")
    try:
        intent = llm_query_service.classify_main_intent(query)
        print(f"主意图分类结果: {intent}")
        return {"main_intent": intent, "error_message": None} # 清除之前的错误（如果有）
    except Exception as e:
        error_msg = f"主意图分类失败: {e}"
        print(error_msg)
        # 分类失败，也归入"确认/其他"分支进行处理
        return {"main_intent": "confirm_other", "error_message": error_msg}

def _route_after_main_intent(state: GraphState) -> Literal[
    "classify_query_analysis_node", # 查询/分析分支
    "handle_modify_intent",       # 修改分支
    "handle_add_intent",          # 新增分支
    "handle_delete_intent",       # 删除分支
    "handle_reset",               # 重置分支
    "handle_confirm_other"        # 确认/其他分支
]:
    """
    路由逻辑：根据主意图分类结果决定下一个节点。
    """
    intent = state.get("main_intent")
    print(f"---路由逻辑: 根据主意图 '{intent}' 决定走向---")
    if intent == "query_analysis":
        return "classify_query_analysis_node"
    elif intent == "modify":
        return "handle_modify_intent"
    elif intent == "add":
        return "handle_add_intent"
    elif intent == "delete":
        return "handle_delete_intent"
    elif intent == "reset":
        return "handle_reset"
    else: # "confirm_other" 或 错误/未知
        return "handle_confirm_other"

# --- 查询/分析 子意图路由 ---

def classify_query_analysis_node(state: GraphState) -> Dict[str, Any]:
    """
    路由节点：调用 LLM 服务对查询/分析意图进行子分类。
    """
    print("---路由节点: 查询/分析 子意图分类---")
    query = state.get("query", "")
    try:
        sub_intent = llm_query_service.classify_query_analysis_intent(query)
        print(f"查询/分析 子意图分类结果: {sub_intent}")
        return {"query_analysis_intent": sub_intent, "error_message": None}
    except Exception as e:
        error_msg = f"查询/分析子意图分类失败: {e}"
        print(error_msg)
        # 分类失败，默认按查询处理
        return {"query_analysis_intent": "query", "error_message": error_msg}

def _route_query_or_analysis(state: GraphState) -> Literal[
    "query",  # 修正：返回逻辑分支名
    "analysis" # 修正：返回逻辑分支名
]:
    """
    路由逻辑：根据查询/分析子意图决定下一个逻辑分支。
    """
    sub_intent = state.get("query_analysis_intent")
    print(f"---路由逻辑: 根据查询/分析子意图 '{sub_intent}' 决定走向---")
    if sub_intent == "analysis":
        return "analysis" # 返回 'analysis'
    else: # "query" 或 错误/默认
        return "query"    # 返回 'query'

# --- 查询后路由 ---

def route_after_query_execution_node(state: GraphState) -> Dict[str, Any]:
    """
    路由节点：在 SQL 执行后准备进行路由决策。
    本身不执行路由，仅用于连接。
    """
    print("---路由节点: 准备根据 SQL 执行结果路由---")
    # 可以在这里打印一些调试信息
    error_msg = state.get("error_message")
    sql_result = state.get("sql_result")
    print(f"  错误信息: {error_msg}")
    print(f"  SQL 结果: {sql_result}")
    return {} # 路由逻辑在条件边处理

def _route_after_query_execution(state: GraphState) -> Literal[
    "format_query_result",      # 查询成功且有结果
    "analyze_analysis_result",  # 分析成功且有结果
    "handle_query_not_found",   # 查询成功但无结果
    "handle_analysis_no_data",  # 分析成功但无结果
    "handle_clarify_query",     # 查询执行/API失败
    "handle_clarify_analysis"   # 分析执行/API失败
]:
    """
    路由逻辑：根据 SQL 执行结果和意图决定下一步。
    """
    error_message = state.get("error_message")
    sql_result = state.get("sql_result")
    intent = state.get("query_analysis_intent", "query") # 默认为查询

    print(f"---路由逻辑: 根据 SQL 执行结果路由 (意图: {intent})---")

    if error_message:
        print(f"检测到执行错误: {error_message}")
        # final_answer 可能已在 execute_sql_query_action 中被设置
        if intent == "analysis":
            return "handle_clarify_analysis"
        else:
            return "handle_clarify_query"
    elif data_processor.is_query_result_empty(sql_result):
        print("SQL 执行成功，但结果为空。")
        if intent == "analysis":
            return "handle_analysis_no_data"
        else:
            return "handle_query_not_found"
    else:
        print("SQL 执行成功且有结果。")
        if intent == "analysis":
            return "analyze_analysis_result" # TODO: 实现此节点
        else:
            return "format_query_result"     # TODO: 实现此节点

# --- 其他流程的路由节点 (占位) ---
# def route_main_intent(state: GraphState) -> str:
#     print("---路由: 主要意图---")
#     # ... 根据意图分类结果返回不同的路由目标 ...
#     return "some_action_node" 