# confirmation_router.py: 包含保存确认流程的路由节点和逻辑。

from typing import Literal, Dict, Any

from langgraph_crud_app.graph.state import GraphState
# from langgraph_crud_app.services.llm import llm_flow_control_service # 稍后会用到
from langgraph_crud_app.services.llm import llm_flow_control_service # 导入 LLM 服务

# --- 确认流程路由节点 (空节点，仅作路由分支点) ---

def route_confirmation_entry(state: GraphState) -> Dict[str, Any]:
    """
    路由节点：确认流程的入口。
    根据 save_content 状态决定是检查已暂存的操作还是尝试暂存新操作。
    """
    print("---路由节点: 确认流程入口---")
    # 此节点本身不改变状态，仅用于路由决策
    return {}

def stage_operation_node(state: GraphState) -> Dict[str, Any]:
    """
    路由节点：尝试暂存操作（修改、新增、删除）。
    """
    print("---路由节点: 尝试暂存操作---")
    return {}

def check_staged_operation_node(state: GraphState) -> Dict[str, Any]:
    """
    路由节点：检查已暂存的操作类型。
    """
    print("---路由节点: 检查已暂存操作---")
    return {}

def ask_confirm_modify_node(state: GraphState) -> Dict[str, Any]:
    """
    路由节点：向用户询问是否确认修改。
    """
    print("---路由节点: 询问是否确认修改---")
    return {}

# --- 确认流程路由逻辑 ---

def _route_confirmation_entry_logic(state: GraphState) -> Literal[
    "check_staged_operation_node",
    "stage_operation_node"
]:
    """
    路由逻辑：确认流程入口决策。
    """
    save_content = state.get("save_content")
    print(f"---路由逻辑: 确认入口，save_content 为 '{save_content}'---")
    if save_content:
        # 如果已有待确认操作，则去检查是什么操作
        return "check_staged_operation_node"
    else:
        # 如果没有待确认操作，则尝试根据当前状态暂存一个
        return "stage_operation_node"

def _stage_operation_logic(state: GraphState) -> Literal[
    "stage_modify_action",
    "stage_add_action",
    "stage_delete_action",
    "stage_combined_action",
    "handle_nothing_to_stage"
]:
    """
    路由逻辑：判断应该暂存哪种操作。
    对应 Dify 节点: 1742272764317
    修改：增加对 content_delete 和 content_combined 的检查。
    """
    content_modify = state.get("content_modify")
    content_new = state.get("content_new")
    content_delete = state.get("content_delete")
    content_combined = state.get("content_combined")

    print(f"---路由逻辑: 尝试暂存，modify: {'有' if content_modify else '无'}, new: {'有' if content_new else '无'}, delete: {'有' if content_delete else '无'}, combined: {'有' if content_combined else '无'}---")

    if content_modify:
        return "stage_modify_action"
    elif content_new:
        return "stage_add_action"
    elif content_delete:
        return "stage_delete_action"
    elif content_combined:
        return "stage_combined_action"
    else:
        return "handle_nothing_to_stage"

def _check_staged_operation_logic(state: GraphState) -> Literal[
    "ask_confirm_modify_node",
    "handle_invalid_save_state"
]:
    """
    路由逻辑：根据 save_content 判断具体是哪种确认流程。
    对应 Dify 节点: 1742350590415
    修改：增加对 "删除路径" 的检查。
    """
    save_content = state.get("save_content")
    content_modify = state.get("content_modify")
    content_new = state.get("content_new")
    content_delete = state.get("content_delete")
    content_combined = state.get("content_combined")
    lastest_content_production = state.get("lastest_content_production")
    delete_show = state.get("delete_show")

    print(f"---路由逻辑: 检查暂存操作，save_content: '{save_content}', modify: {'有' if content_modify else '无'}, new: {'有' if content_new else '无'}, delete: {'有' if content_delete else '无'}, combined: {'有' if content_combined else '无'}, production: {'有' if lastest_content_production else '无'}, delete_show: {'有' if delete_show else '无'}---")

    if save_content == "修改路径" and content_modify and lastest_content_production:
        print("路由到修改确认询问")
        return "ask_confirm_modify_node"
    elif save_content == "新增路径" and content_new and lastest_content_production:
        print("路由到新增确认询问 (复用修改逻辑)")
        return "ask_confirm_modify_node"
    elif save_content == "复合路径" and content_combined and lastest_content_production:
        print("路由到复合操作确认询问 (复用修改逻辑)")
        return "ask_confirm_modify_node"
    elif save_content == "删除路径" and content_delete:
        print("路由到删除确认询问 (复用修改逻辑)")
        return "ask_confirm_modify_node"
    else:
        print(f"警告: save_content ('{save_content}') 与实际状态不一致或缺少必要数据。")
        return "handle_invalid_save_state"

# _ask_confirm_modify_logic 将被新增和修改流程复用
def _ask_confirm_modify_logic(state: GraphState) -> Literal[
    "execute_operation_action", # 改为通用名称
    "cancel_save_action"     # 用户取消或回复不明确
]:
    """
    路由逻辑：判断用户是否确认操作 (修改/新增/删除)。
    对应 Dify 节点: 1742350663522 / 1742438547791 / 1742520713951
    """
    query = state.get("user_query", "")
    save_content = state.get("save_content")
    print(f"---路由逻辑: 判断用户确认 '{save_content}', 输入: '{query}'---")

    # 使用通用的 yes/no 分类器
    confirmation = llm_flow_control_service.classify_yes_no(query)

    if confirmation == "yes":
        print(f"用户确认 '{save_content}'，执行...")
        return "execute_operation_action" # 路由到统一的执行节点
    else: # "no" 或 "unknown"
        print(f"用户取消 '{save_content}' 或回复不明确，取消保存...")
        return "cancel_save_action" 