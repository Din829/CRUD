# mre_state_loss.py
# 最小复现案例：测试 LangGraph 节点间状态传递

import sys
from pathlib import Path
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

# 确保能导入 langgraph
try:
    import langgraph
except ImportError:
    print("错误：请确保已安装 langgraph (`pip install langgraph`) 以及 langgraph-checkpoint-sqlite (`pip install langgraph-checkpoint-sqlite`)")
    sys.exit(1)

# --- 最小状态定义 ---
class MinimalState(TypedDict):
    """一个极其简单的状态，只包含我们要测试的字段"""
    my_list: Optional[List[Dict[str, Any]]] = None
    step_counter: int # 用于跟踪执行步骤

# --- 节点函数 ---
def set_list_node(state: MinimalState) -> Dict[str, Any]:
    """设置状态中的 my_list"""
    print(f"--- 节点: set_list_node (计数器: {state['step_counter']}) ---")
    new_list = [{"a": 1, "step": state['step_counter']}]
    print(f"    返回更新: {{'my_list': {new_list}}})")
    # 只返回要更新的部分
    return {"my_list": new_list, "step_counter": state['step_counter'] + 1}

def get_list_node(state: MinimalState) -> Dict[str, Any]:
    """尝试读取状态中的 my_list"""
    print(f"--- 节点: get_list_node (计数器: {state['step_counter']}) ---")
    retrieved_list = state.get("my_list")
    print(f"    读取状态 'my_list': {retrieved_list}")
    if retrieved_list is None:
        print("    !!! 状态 'my_list' 未被读取到 !!!")
    else:
        print("    状态 'my_list' 读取成功。")
    # 返回空字典，不更新状态，仅增加计数器
    return {"step_counter": state['step_counter'] + 1}

# --- 新增：简单的路由函数 ---
def simple_router(state: MinimalState) -> str:
    """一个简单的路由函数，总是返回 'continue'"""
    print(f"--- 路由函数: simple_router (计数器: {state['step_counter']}) ---")
    # 可以在这里也打印状态，以供调试
    print(f"    路由函数接收到的 'my_list': {state.get('my_list')}") 
    # 实际路由逻辑（这里总是继续）
    return "continue"

# --- 构建图 ---
builder = StateGraph(MinimalState)

builder.add_node("set_list", set_list_node)
builder.add_node("get_list", get_list_node)

# --- 修改：使用条件边连接 --- 
# 移除直接边
# builder.add_edge("set_list", "get_list") 

# 添加条件边
builder.add_conditional_edges(
    "set_list",
    simple_router, # 使用新的路由函数
    {
        "continue": "get_list", # 如果路由返回 "continue"，则转到 get_list
        "stop": END # 添加一个假想的停止分支（虽然不会被调用）
    }
)

# 设置入口和结束
builder.set_entry_point("set_list")
builder.add_edge("get_list", END)

# --- 编译和运行 ---
# 使用内存检查点，避免文件系统问题干扰
memory = SqliteSaver.from_conn_string(":memory:")
# 确保正确获取检查点实例
with memory as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)

    # 定义一个线程 ID 用于会话
    thread_id = "mre-thread-1"
    config = {"configurable": {"thread_id": thread_id}}

    # 初始状态
    initial_state = {"step_counter": 0}

    print("\n--- 开始运行最小复现案例 ---")
    print(f"初始状态: {initial_state}")

    # 运行图
    final_state = graph.invoke(initial_state, config=config)

    print("\n--- 运行结束 ---")
    print(f"最终状态: {final_state}")

    # 检查最终状态是否包含 my_list
    if final_state and final_state.get("my_list"):
        print("\n结论：状态 'my_list' 在最终状态中存在。")
    else:
        print("\n结论：状态 'my_list' 在最终状态中不存在或为 None。") 