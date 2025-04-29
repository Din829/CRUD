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
    # "stage_add_action", # 未来扩展
    # "stage_delete_action", # 未来扩展
    "handle_nothing_to_stage" # 无法确定暂存哪个操作
]:
    """
    路由逻辑：判断应该暂存哪种操作（目前仅实现修改）。
    对应 Dify 节点: 1742272764317
    """
    content_modify = state.get("content_modify")
    # content_new = state.get("content_new") # 未来扩展
    # delete_show = state.get("delete_show") # 未来扩展

    print(f"---路由逻辑: 尝试暂存，content_modify: {'非空' if content_modify else '空'}---")

    # 简化版：仅检查 content_modify 是否有内容
    if content_modify:
        return "stage_modify_action"
    # elif content_new:
    #     return "stage_add_action"
    # elif delete_show:
    #     return "stage_delete_action"
    else:
        # 如果修改、新增、删除都没有内容，则无法暂存
        return "handle_nothing_to_stage"

def _check_staged_operation_logic(state: GraphState) -> Literal[
    "ask_confirm_modify_node",
    # "ask_confirm_add_node", # 未来扩展
    # "ask_confirm_delete_node", # 未来扩展
    "handle_invalid_save_state" # save_content 状态无效或与其他状态不符
]:
    """
    路由逻辑：根据 save_content 判断具体是哪种确认流程。
    对应 Dify 节点: 1742350590415
    """
    save_content = state.get("save_content")
    content_modify = state.get("content_modify")
    # content_new = state.get("content_new") # 未来扩展
    # delete_show = state.get("delete_show") # 未来扩展

    print(f"---路由逻辑: 检查暂存操作，save_content: '{save_content}', content_modify: {'非空' if content_modify else '空'}---")

    if save_content == "修改路径" and content_modify:
        return "ask_confirm_modify_node"
    # elif save_content == "新增路径" and content_new:
    #     return "ask_confirm_add_node"
    # elif save_content == "删除路径" and delete_show:
    #     return "ask_confirm_delete_node"
    else:
        # 如果 save_content 的值与实际状态不符（例如标记为修改但 content_modify 为空）
        return "handle_invalid_save_state"

# _ask_confirm_modify_logic 将在下一步实现，需要调用 LLM 服务
def _ask_confirm_modify_logic(state: GraphState) -> Literal[
    "execute_modify_action", # 用户确认修改
    "cancel_save_action"     # 用户取消修改或回复不明确
]:
    """
    路由逻辑：判断用户是否确认修改。
    对应 Dify 节点: 1742350663522
    """
    query = state.get("query", "")
    print(f"---路由逻辑: 判断用户确认修改, 输入: '{query}'---")

    confirmation = llm_flow_control_service.classify_yes_no(query)

    if confirmation == "yes":
        print("用户确认修改，执行...")
        return "execute_modify_action"
    else: # "no" 或 "unknown"
        print("用户取消修改或回复不明确，取消保存...")
        return "cancel_save_action" 