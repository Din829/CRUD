# initialization_router.py: 包含初始化流程的路由逻辑。

from typing import Literal, Dict, Any
from langgraph_crud_app.graph.state import GraphState

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
    # 读取 error_message, 但这里的 error_message 是上一轮次可能遗留的，
    # route_initialization_node 会在返回时将其清空。
    # _get_initialization_route 在 route_initialization_node 之后被 langgraph 引擎调用，
    # 所以此时它读到的 error_message 已经是被 route_initialization_node 清理过的 None。
    # 因此，此处的 error_message 检查主要针对初始化序列内部发生的错误，
    # 而不是上一轮用户请求的错误。
    error_message_from_current_init_flow = state.get("error_message")
    if error_message_from_current_init_flow:
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
    路由节点：图的入口。检查状态、打印信息，并重置处理新请求前应被清除的通用反馈状态字段。
    Staging content for multi-turn operations (like content_modify, delete_show) are NOT reset here.
    """
    print("---路由节点: 检查初始化状态 (打印信息)---")
    # 打印检查信息 (可以保留或根据需要调整)
    biaojiegou_save = state.get("biaojiegou_save")
    table_names = state.get("table_names")
    data_sample = state.get("data_sample")
    # error_message 在这里读取的是上一轮可能残留的值，之后会被重置
    error_message_before_reset = state.get("error_message") 

    missing_data = []
    if not biaojiegou_save:
        missing_data.append("Schema (biaojiegou_save)")
    if not table_names:
        missing_data.append("Table Names (table_names)")
    if not data_sample:
        missing_data.append("Data Sample (data_sample)")

    if missing_data:
        print(f"状态检查：缺少数据: {', '.join(missing_data)}")
    else:
        print("状态检查：必需的元数据 (Schema, Tables, Sample) 存在。")

    if error_message_before_reset:
        print(f"状态检查：检测到来自上一轮的错误消息: {error_message_before_reset}")
    else:
        print("状态检查：未检测到来自上一轮的错误消息。")

    # Reset per-turn feedback/error states.
    # Crucially, DO NOT reset fields involved in staging multi-turn operations
    # like content_*, delete_show, save_content, lastest_content_production, etc.
    return {
        "final_answer": None,
        "error_message": None, 
        "api_call_result": None, 
        
        "modify_error_message": None,
        "add_error_message": None,
        "delete_error_message": None,
        
        "delete_preview_text": None, # Specific preview text for a turn's output
        "add_preview_text": None,    # Specific preview text for a turn's output
        "pending_confirmation_type": None # 新增：清除待确认类型
    } 