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