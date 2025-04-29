# main_router.py: 包含主意图分类和路由逻辑。

from typing import Literal, Dict, Any
from langgraph_crud_app.graph.state import GraphState
# from langgraph_crud_app.services import llm_query_service # 旧路径
from langgraph_crud_app.services.llm import llm_query_service # 修正路径

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
    "route_confirmation_entry"  # 新的确认流程入口节点
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
        return "route_confirmation_entry" 