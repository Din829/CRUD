# routers.py: 包含负责条件路由和逻辑流控制的 LangGraph 节点函数。 

from typing import Literal

# 导入状态定义
# 使用绝对导入路径
from langgraph_crud_app.graph.state import GraphState

# --- 初始化流程路由节点 ---

def route_initialization(state: GraphState) -> Literal["start_initialization", "continue_to_main_flow", "handle_error"]:
    """
    路由节点：检查必要的初始化数据是否已存在于状态中。
    对应 Dify 条件分支节点: '1743973729940'

    Args:
        state: 当前图状态。

    Returns:
        一个字符串，指示下一个要执行的节点:
        - "start_initialization": 如果缺少任何必要的初始化数据。
        - "continue_to_main_flow": 如果所有必要数据都存在。
        - "handle_error": 如果在之前的步骤中记录了错误。
    """
    print("---路由: 检查初始化状态---")
    error_message = state.get("error_message")
    if error_message:
        print(f"检测到错误，路由到错误处理: {error_message}")
        # 注意：Dify 的原始流程似乎没有在初始化失败时停止，这里我们添加一个错误处理路径
        # 如果想严格模拟 Dify (即忽略初始化错误继续)，可以移除这个检查或让其返回 "continue_to_main_flow"
        return "handle_error"

    biaojiegou_save = state.get("biaojiegou_save")
    table_names = state.get("table_names")
    data_sample = state.get("data_sample")

    # Dify 条件是检查三者是否都 'not empty'
    # 对于列表 table_names，not empty 意味着列表本身不为 None 且包含元素
    # 对于字符串，not empty 意味着字符串不为 None 且不为空字符串 (或 '{}' 对于 JSON 字符串)
    if biaojiegou_save and biaojiegou_save != "{}" and table_names and data_sample and data_sample != "{}":
        print("所有初始化数据已存在，继续主流程。")
        return "continue_to_main_flow"
    else:
        missing = []
        if not (biaojiegou_save and biaojiegou_save != "{}"):
            missing.append("Schema")
        if not table_names:
            missing.append("表名")
        if not (data_sample and data_sample != "{}"):
            missing.append("数据示例")
        print(f"缺少初始化数据: {', '.join(missing)}。开始初始化流程。")
        return "start_initialization"

# --- 其他流程的路由节点 (占位) ---
# def route_main_intent(state: GraphState) -> str:
#     print("---路由: 主要意图---")
#     # ... 根据意图分类结果返回不同的路由目标 ...
#     return "some_action_node" 