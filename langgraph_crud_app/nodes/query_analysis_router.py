# query_analysis_router.py: 包含查询/分析子流程的路由逻辑。

from typing import Literal, Dict, Any
from langgraph_crud_app.graph.state import GraphState
from langgraph_crud_app.services import llm_query_service, data_processor

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