# main_router.py: 包含主意图分类和路由逻辑。

from typing import Literal, Dict, Any
from langgraph_crud_app.graph.state import GraphState
from langgraph_crud_app.services.llm import llm_query_service, llm_flow_control_service

# --- 主意图路由 ---

def classify_main_intent_node(state: GraphState) -> Dict[str, Any]:
    """
    路由节点：调用 LLM 服务对用户查询进行主意图分类。
    """
    print("---路由节点: 主意图分类---")
    user_query = state.get("user_query", "")
    # biaojiegou_save = state.get("biaojiegou_save") # llm_query_service.classify_main_intent 目前不使用这些
    # table_names = state.get("table_names")       # llm_query_service.classify_main_intent 目前不使用这些

    if not user_query:
        print("警告: 在主意图分类节点未获取到 user_query。")
        return {"main_intent": "confirm_other", "error_message": "未获取到有效的用户查询"}

    # # 确保必要的元数据存在才进行分类 - llm_query_service.classify_main_intent 目前不使用这些
    # if not biaojiegou_save or not table_names:
    #     error_msg = "主意图分类失败: 缺少必要的数据库Schema或表名信息。"
    #     print(error_msg)
    #     return {"main_intent": "confirm_other", "error_message": error_msg}

    try:
        classification_result = llm_query_service.classify_main_intent(user_query)
        intent_string = "confirm_other" # 默认值
        
        if isinstance(classification_result, dict):
            # 如果是字典，尝试获取 'intent' 键
            intent_string = classification_result.get("intent", "confirm_other")
            if not isinstance(intent_string, str) or not intent_string.strip():
                print(f"警告: 从LLM分类结果字典中获取的意图 '{intent_string}' 不是有效字符串，默认为 confirm_other。")
                intent_string = "confirm_other"
        elif isinstance(classification_result, str) and classification_result.strip():
            # 如果是有效字符串，直接使用
            intent_string = classification_result
            # 可选: 验证 intent_string 是否是已知的有效意图之一
            # valid_intents = ["query_analysis", "modify", "add", "delete", "composite", "confirm_other", "reset"]
            # if intent_string not in valid_intents:
            #     print(f"警告: LLM直接返回的意图 '{intent_string}' 不是已知有效意图，默认为 confirm_other。")
            #     intent_string = "confirm_other"
        else:
            print(f"警告: LLM分类结果 '{classification_result}' 类型未知或为空，默认为 confirm_other。")

        print(f"主意图分类结果: {classification_result}, 提取的意图字符串: {intent_string}")
        return {
            "main_intent": intent_string,
            "main_intent_classification_details": classification_result if isinstance(classification_result, dict) else {"intent": intent_string, "details": "LLM directly returned string."},
            "error_message": None
        } # 清除之前的错误（如果有）
    except Exception as e:
        error_msg = f"主意图分类失败: {e}"
        print(error_msg)
        # 分类失败，也归入"确认/其他"分支进行处理
        return {
            "main_intent": "confirm_other",
            "main_intent_classification_details": None, # 确保在错误时也设置
            "error_message": error_msg
        }

def _route_after_main_intent(state: GraphState):
    """根据 LLM 分类的主意图进行路由。"""
    print(f"--- Routing based on Main Intent: {state.get('main_intent')} ---")
    intent = state.get("main_intent")

    if intent == "query_analysis":
        return "continue_to_query_analysis"
    elif intent == "modify":
        return "continue_to_modify"
    elif intent == "add": # 为 'add' 意图添加的分支
        # TODO: 根据 Dify 节点 1742437386323 添加预检查
        # 检查 content_new 或 save_content 是否已填充？
        # 暂时直接路由到新增流程开始
        print("Routing to Add flow")
        return "start_add_flow"
    elif intent == "composite": # 新增：处理复合意图
        print("Routing to Composite flow")
        return "start_composite_flow"
    elif intent == "delete": # 为 'delete' 意图添加的分支 (占位符)
        print("Routing to Delete flow (placeholder)")
        return "start_delete_flow"
    elif intent == "reset":
        return "reset_flow"
    elif intent == "confirm_other":
        return "continue_to_confirmation"
    else:
        print("未知或模糊意图，路由到确认/回退。")
        return "continue_to_confirmation" # 回退或处理歧义 