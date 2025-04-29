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
    路由节点：检查状态并打印信息。修改：总是重置错误消息。
    """
    print("---路由节点: 检查初始化状态 (打印信息)---")
    # 打印检查信息
    biaojiegou_save = state.get("biaojiegou_save")
    table_names = state.get("table_names")
    data_sample = state.get("data_sample")
    error_message = state.get("error_message")

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

    if error_message:
        print(f"状态检查：检测到错误消息: {error_message}")
    else:
        print("状态检查：未检测到错误消息。")

    # 修改：总是返回一个字典，并将 error_message 重置为 None
    # 这样可以确保每次运行都从干净的错误状态开始，避免残留错误干扰路由
    return {"error_message": None} 