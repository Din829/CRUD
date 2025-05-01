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
    "stage_add_action", # 添加新增暂存动作
    # "stage_delete_action", # 未来扩展
    "handle_nothing_to_stage" # 无法确定暂存哪个操作
]:
    """
    路由逻辑：判断应该暂存哪种操作。
    对应 Dify 节点: 1742272764317
    """
    content_modify = state.get("content_modify")
    content_new = state.get("content_new") # 检查新增内容
    # delete_show = state.get("delete_show") # 未来扩展

    print(f"---路由逻辑: 尝试暂存，content_modify: {'非空' if content_modify else '空'}, content_new: {'非空' if content_new else '空'}---")

    # 优先级：修改 > 新增 > 删除 (暂定)
    if content_modify:
        return "stage_modify_action"
    elif content_new:
        return "stage_add_action" # 路由到新增暂存
    # elif delete_show:
    #     return "stage_delete_action"
    else:
        # 如果修改、新增、删除都没有内容，则无法暂存
        return "handle_nothing_to_stage"

def _check_staged_operation_logic(state: GraphState) -> Literal[
    "ask_confirm_modify_node",
    "ask_confirm_add_node", # 添加新增确认询问节点
    # "ask_confirm_delete_node", # 未来扩展
    "handle_invalid_save_state" # save_content 状态无效或与其他状态不符
]:
    """
    路由逻辑：根据 save_content 判断具体是哪种确认流程。
    对应 Dify 节点: 1742350590415
    """
    save_content = state.get("save_content")
    content_modify = state.get("content_modify")
    content_new = state.get("content_new") # 获取新增内容状态
    # delete_show = state.get("delete_show") # 未来扩展
    lastest_content_production = state.get("lastest_content_production") # 获取待生产数据

    print(f"---路由逻辑: 检查暂存操作，save_content: '{save_content}', content_modify: {'非空' if content_modify else '空'}, content_new: {'非空' if content_new else '空'}, lastest_content_production: {'非空' if lastest_content_production else '空'}---")

    if save_content == "修改路径" and content_modify and lastest_content_production:
        # 假设修改也需要 lastest_content_production 非空
        return "ask_confirm_modify_node"
    elif save_content == "新增路径" and content_new and lastest_content_production:
        # 检查新增路径，需要预览文本和待生产数据都存在
        # 复用 ask_confirm_modify_node 和 _ask_confirm_modify_logic, 因为 LLM 判断逻辑相同
        print("路由到新增确认询问 (复用修改逻辑)")
        return "ask_confirm_modify_node" 
    # elif save_content == "删除路径" and delete_show:
    #     return "ask_confirm_delete_node"
    else:
        # 如果 save_content 的值与实际状态不符
        print(f"警告: save_content ('{save_content}') 与实际状态不一致。")
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