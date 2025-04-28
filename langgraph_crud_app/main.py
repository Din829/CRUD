# main.py: LangGraph 应用的主入口点。 

import sys
import os
# Correct import path after installing langgraph-checkpoint-sqlite
from langgraph.checkpoint.sqlite import SqliteSaver # 用于持久化状态
import traceback # 导入 traceback

# 确保证项目根目录在 Python 路径中，以便绝对导入能够工作
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
# Add the parent directory (DifyLang) to sys.path instead
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langgraph_crud_app.graph.graph_builder import build_graph
# GraphState 导入不再直接需要，因为我们不手动创建它了
# from langgraph_crud_app.graph.state import GraphState

def main():
    """主函数：构建、编译并以交互方式运行 LangGraph 应用。"""
    print("构建 LangGraph 图...")
    graph_builder = build_graph()

    # 使用内存检查点进行测试
    db_conn_string = ":memory:"
    with SqliteSaver.from_conn_string(db_conn_string) as memory:
        print("编译 LangGraph 图...")
        runnable = graph_builder.compile(checkpointer=memory)
        print("图已编译，准备接收输入。")

        # 创建一个唯一的会话 ID
        session_id = "interactive_session"
        config = {"configurable": {"thread_id": session_id}}

        # --- 开始交互式循环 ---
        while True:
            try:
                user_query = input("\n请输入您的问题 (或输入 '退出' 结束): ")
                if user_query.lower() == '退出':
                    print("退出程序。")
                    break
                if not user_query:
                    continue

                print(f"\n--- 处理查询: {user_query} ---")
                inputs = {"query": user_query}
                # 使用 stream_mode="values" 来获取每次更新后的完整状态
                events = runnable.stream(inputs, config=config, stream_mode="values")

                final_state = None
                for event in events:
                    # 在流式处理中打印每个节点的开始和结束可能过于冗长，
                    # 可以根据需要取消注释或添加更精细的日志记录
                    # print(event) # 打印原始事件以供调试
                    final_state = event # 保留最后返回的状态对象

                # 在循环结束后打印最终结果
                print("\n--- 查询处理完成 ---")
                if final_state:
                    print(f"  最终答案: {final_state.get('final_answer')}")
                    if final_state.get('error_message'):
                        print(f"  错误信息: {final_state.get('error_message')}")
                else:
                    print("  未获取到最终状态或答案。")

            except KeyboardInterrupt:
                print("\n检测到中断，退出程序。")
                break
            except Exception as e:
                print(f"\n处理查询时发生错误: {e}")
                traceback.print_exc() # 打印详细错误堆栈
                print("您可以尝试下一个查询，或输入 '退出'。")
        # --- 交互式循环结束 ---

if __name__ == "__main__":
    main() 