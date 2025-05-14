# query_analysis_router.py: 包含查询/分析子流程的路由逻辑。

from typing import Literal, Dict, Any
from langgraph_crud_app.graph.state import GraphState
from langgraph_crud_app.services import data_processor
from langgraph_crud_app.services.llm import llm_query_service

# --- 查询/分析 子意图路由 ---

def classify_query_analysis_node(state: GraphState) -> Dict[str, Any]:
    """
    路由节点：调用 LLM 服务对用户查询进行子意图分类 (query/analysis)。
    LLM 服务预期直接返回 "query" 或 "analysis" 字符串。
    """
    print("---路由节点: 查询/分析子意图分类---")
    query = state.get("user_query", "")
    try:
        # llm_query_service.classify_query_analysis_intent 预期返回 "query" 或 "analysis" 字符串
        sub_intent_str = llm_query_service.classify_query_analysis_intent(query)
        print(f"查询/分析 子意图分类结果 (直接字符串): {sub_intent_str}")
        # 确保存储的是字符串
        if sub_intent_str not in ["query", "analysis"]:
            print(f"警告: LLM服务 classify_query_analysis_intent 返回了非预期的值 '{sub_intent_str}', 将默认为 'query'")
            sub_intent_str = "query" # 安全回退
        return {"query_analysis_intent": sub_intent_str, "error_message": None}
    except Exception as e:
        error_msg = f"查询/分析子意图分类失败: {e}"
        print(error_msg)
        # 分类失败，默认按查询处理 (字符串)
        return {"query_analysis_intent": "query", "error_message": error_msg}

def _route_query_or_analysis(state: GraphState) -> Literal[
    "query",
    "analysis"
]:
    """
    路由逻辑：根据查询/分析子意图决定下一个逻辑分支。
    预期 state.get("query_analysis_intent") 直接是 "query" 或 "analysis" 字符串。
    """
    actual_intent_str = state.get("query_analysis_intent", "query") # 直接获取，它应该是字符串 "query" 或 "analysis"
    print(f"---路由逻辑: _route_query_or_analysis - 接收到的 actual_intent_str: '{actual_intent_str}'---")
    if actual_intent_str == "analysis":
        print(f"---路由决策: 返回 'analysis'---")
        return "analysis"
    else: # "query" 或任何其他情况 (包括None，但classify_node会给默认值 "query")
        print(f"---路由决策: 返回 'query' (因为 actual_intent_str is '{actual_intent_str}')---")
        return "query"

# --- 查询后路由 ---

def route_after_query_execution_node(state: GraphState) -> Dict[str, Any]:
    """
    路由节点：在 SQL 执行后准备进行路由决策。
    本身不执行路由，仅用于连接。
    """
    print("---路由节点: 准备根据 SQL 执行结果路由---")
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
    预期 state.get("query_analysis_intent") 直接是 "query" 或 "analysis" 字符串。
    """
    error_message = state.get("error_message")
    sql_result = state.get("sql_result")
    
    actual_intent_str = state.get("query_analysis_intent", "query") # 直接获取，默认为"query"

    print(f"---路由逻辑: _route_after_query_execution - 接收到的 actual_intent_str: '{actual_intent_str}'---")

    if error_message:
        print(f"检测到执行错误: {error_message}")
        if actual_intent_str == "analysis":
            return "handle_clarify_analysis"
        else:
            return "handle_clarify_query"
    elif data_processor.is_query_result_empty(sql_result):
        print("SQL 执行成功，但结果为空。")
        if actual_intent_str == "analysis":
            return "handle_analysis_no_data"
        else:
            return "handle_query_not_found"
    else:
        print("SQL 执行成功且有结果。")
        if actual_intent_str == "analysis":
            print(f"---路由决策: 返回 'analyze_analysis_result' (因为 actual_intent_str == 'analysis')---")
            return "analyze_analysis_result"
        else:
            print(f"---路由决策: 返回 'format_query_result' (因为 actual_intent_str is '{actual_intent_str}')---")
            return "format_query_result" 