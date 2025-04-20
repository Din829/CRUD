# main.py: LangGraph 应用的主入口点。 

import sys
import os
from langgraph.checkpoint.sqlite import SqliteSaver # 用于持久化状态

# 确保证项目根目录在 Python 路径中，以便绝对导入能够工作
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langgraph_crud_app.graph.graph_builder import build_graph
from langgraph_crud_app.graph.state import GraphState

def main():
    """主函数：构建、编译并运行 LangGraph 应用。"""
    print("构建 LangGraph 图...")
    graph_builder = build_graph()

    # 设置检查点 (用于持久化状态，这里使用 SQLite)
    # 这允许图在多次调用之间保持其状态 (例如 biaojiegou_save)
    memory = SqliteSaver.from_conn_string(":memory:") # 使用内存数据库进行简单测试
    # 对于持久化存储，可以使用文件路径: SqliteSaver.from_conn_string("checkpoints.sqlite")

    print("编译 LangGraph 图...")
    # runnable = graph_builder.compile()
    # 使用检查点进行编译
    runnable = graph_builder.compile(checkpointer=memory)

    print("图已编译。")

    # --- 运行示例 ---
    # 创建一个唯一的会话 ID (对于有状态的图是必需的)
    # 每次调用都需要提供 config，至少包含 thread_id
    session_id = "user_session_1"
    config = {"configurable": {"thread_id": session_id}}

    # 第一次调用 (假设状态为空，应触发初始化流程)
    print("\n--- 第一次调用 (触发初始化) ---")
    # 输入需要与 GraphState 中的 'query' 字段匹配
    inputs = {"query": "你好"} # 初始查询内容不重要，主要是为了启动流程
    try:
        # 使用 stream 方法逐步获取输出和状态更新
        events = runnable.stream(inputs, config=config, stream_mode="values")
        final_state = None
        for event in events:
            # event 通常是当前完整的 GraphState
            # print(f"\n状态更新: {event}\n")
            final_state = event # 保留最后的状态

        print("\n--- 第一次调用完成 --- Final State:")
        if final_state:
            # 打印最终状态中的关键信息
            print(f"  Schema Saved: {final_state.get('biaojiegou_save') is not None}")
            print(f"  Table Names: {final_state.get('table_names')}")
            print(f"  Sample Data Saved: {final_state.get('data_sample') is not None}")
            print(f"  Final Answer: {final_state.get('final_answer')}")
            print(f"  Error Message: {final_state.get('error_message')}")
        else:
            print(" 未获取到最终状态。")

    except Exception as e:
        print(f"\n运行图时发生错误: {e}")
        import traceback
        traceback.print_exc()

    # 第二次调用 (假设第一次成功，应跳过初始化)
    print("\n--- 第二次调用 (应跳过初始化) ---")
    inputs = {"query": "查询订单"} # 不同的查询，主要看是否跳过初始化
    try:
        events = runnable.stream(inputs, config=config, stream_mode="values")
        final_state_2 = None
        for event in events:
            final_state_2 = event

        print("\n--- 第二次调用完成 --- Final State:")
        if final_state_2:
            print(f"  Final Answer: {final_state_2.get('final_answer')}")
            print(f"  Error Message: {final_state_2.get('error_message')}")
        else:
            print(" 未获取到最终状态。")

    except Exception as e:
        print(f"\n运行图时发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 