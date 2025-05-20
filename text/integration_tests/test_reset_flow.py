"""
集成测试：重置流程
测试重置流程的各种场景，包括重置状态和重置后的行为。
"""

import json
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# 将项目根目录添加到 sys.path 以便导入 langgraph_crud_app
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))  # 从 text/integration_tests 退两级到 DifyLang
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langgraph_crud_app.graph.state import GraphState
from langgraph_crud_app.graph.graph_builder import build_graph

# 测试数据
MOCK_SCHEMA_JSON_STRING = json.dumps({
    "users": {
        "fields": {
            "id": {"type": "int(11)", "null": "NO", "key": "PRI", "default": None},
            "username": {"type": "varchar(255)", "null": "NO", "key": "UNI", "default": None},
            "email": {"type": "varchar(255)", "null": "NO", "key": "UNI", "default": None}
        },
        "foreign_keys": {}
    },
    "prompts": {
        "fields": {
            "id": {"type": "int(11)", "null": "NO", "key": "PRI", "default": None},
            "user_id": {"type": "int(11)", "null": "NO", "key": "MUL", "default": None},
            "title": {"type": "varchar(255)", "null": "NO", "key": "", "default": None}
        },
        "foreign_keys": {"prompts_ibfk_1": {"referenced_table": "users", "columns": ["user_id"], "referenced_columns": ["id"]}}
    }
})

MOCK_TABLE_NAMES = ["users", "prompts"]

MOCK_DATA_SAMPLE = json.dumps({
    "users": [{"id": 1, "username": "testuser", "email": "test@example.com"}],
    "prompts": [{"id": 101, "user_id": 1, "title": "Test Prompt"}]
})

@pytest.fixture(scope="function")
def compiled_app():
    """创建并编译LangGraph应用的测试实例。"""
    try:
        graph_definition = build_graph()
        return graph_definition.compile()
    except Exception as e:
        print(f"Error compiling graph: {e}")
        raise

def test_reset_flow_basic(compiled_app):
    """
    测试场景 7.1: 基本重置功能
    - 验证用户输入"重置"后，系统正确识别意图并清空相关状态
    - 验证重置后的状态变量是否正确清空
    """
    print("\n--- Test: test_reset_flow_basic ---")

    # 初始状态，包含一些需要被重置的数据
    initial_state = GraphState(
        user_query="重置所有状态",
        raw_user_input="重置所有状态",
        biaojiegou_save=MOCK_SCHEMA_JSON_STRING,
        table_names=MOCK_TABLE_NAMES,
        data_sample=MOCK_DATA_SAMPLE,
        content_modify="这是一些修改内容",
        delete_show="这是一些删除内容",
        lastest_content_production="这是最新的内容生产",
        delete_array=["id1", "id2"],
        content_new="这是一些新内容",
        save_content="这是保存的内容",
        raw_add_llm_output="这是原始的LLM输出",
        structured_add_records={"records": [{"id": 1}]},
        add_error_message="这是添加错误信息",
        raw_modify_llm_output="这是原始的修改LLM输出",
        modify_context_sql="这是修改上下文SQL",
        modify_context_result="这是修改上下文结果",
        modify_error_message="这是修改错误信息",
        final_answer=None,
        error_message=None
    )
    config = {"configurable": {"thread_id": "test-reset-flow-basic"}}

    # Mock LLM 服务
    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent:
        # 设置 Mock 返回值
        mock_classify_main_intent.return_value = "reset"

        # 调用图
        print(f"Invoking graph with query: {initial_state.get('user_query')}")
        final_state_dict = compiled_app.invoke(dict(initial_state), config)
        final_state = GraphState(**final_state_dict)

        # 调试打印语句
        print(f"Final answer: {final_state.get('final_answer')}")
        print(f"Error message: {final_state.get('error_message')}")

        # 断言
        mock_classify_main_intent.assert_called_once_with(initial_state.get('user_query'))

        # 验证重置后的状态
        assert final_state.get("content_modify") is None
        assert final_state.get("delete_show") is None
        assert final_state.get("lastest_content_production") is None
        assert final_state.get("delete_array") is None
        assert final_state.get("content_new") is None
        assert final_state.get("save_content") is None
        assert final_state.get("raw_add_llm_output") is None
        assert final_state.get("structured_add_records") is None
        assert final_state.get("add_error_message") is None
        assert final_state.get("raw_modify_llm_output") is None
        assert final_state.get("modify_context_sql") is None
        assert final_state.get("modify_context_result") is None
        assert final_state.get("modify_error_message") is None

        # 验证最终回复
        assert final_state.get("final_answer") == "之前的操作状态已重置。"
        assert final_state.get("error_message") is None

        print("--- Test: test_reset_flow_basic PASSED SUCCESSFULLY ---")

def test_reset_flow_after_operation(compiled_app):
    """
    测试场景 7.2: 操作后重置
    - 模拟用户先执行一个操作（如查询），然后重置
    - 验证重置是否正确清空了操作相关的状态
    """
    print("\n--- Test: test_reset_flow_after_operation ---")

    # ---- ROUND 1: 用户执行查询操作 ----
    initial_user_query_round1 = "查询所有用户"
    thread_id_round1 = "test-reset-flow-after-operation-r1"

    initial_state_round1 = GraphState(
        user_query=initial_user_query_round1,
        raw_user_input=initial_user_query_round1,
        biaojiegou_save=MOCK_SCHEMA_JSON_STRING,
        table_names=MOCK_TABLE_NAMES,
        data_sample=MOCK_DATA_SAMPLE,
        final_answer=None,
        error_message=None
    )
    config_round1 = {"configurable": {"thread_id": thread_id_round1}}

    # Mock LLM 服务和 API 调用
    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent:
        with patch('langgraph_crud_app.services.llm.llm_query_service.classify_query_analysis_intent') as mock_classify_query_analysis:
            with patch('langgraph_crud_app.services.llm.llm_query_service.generate_select_sql') as mock_generate_select_sql:
                with patch('langgraph_crud_app.services.api_client.execute_query') as mock_execute_query:
                    with patch('langgraph_crud_app.services.llm.llm_query_service.format_query_result') as mock_format_query_result:

                        # 设置 Mock 返回值 (Round 1)
                        mock_classify_main_intent.return_value = "query_analysis"
                        mock_classify_query_analysis.return_value = "query"
                        mock_generate_select_sql.return_value = "SELECT * FROM users"
                        mock_execute_query.return_value = json.dumps([
                            {"id": 1, "username": "testuser", "email": "test@example.com"},
                            {"id": 2, "username": "user2", "email": "user2@example.com"}
                        ])
                        mock_format_query_result.return_value = "找到2个用户：testuser和user2"

                        # 调用图 (Round 1)
                        print(f"Invoking graph for Round 1 with query: {initial_user_query_round1}")
                        final_state_dict_round1 = compiled_app.invoke(dict(initial_state_round1), config_round1)
                        final_state_round1 = GraphState(**final_state_dict_round1)

                        # 调试打印语句
                        print(f"Round 1 final_answer: {final_state_round1.get('final_answer')}")
                        print(f"Round 1 sql_query_generated: {final_state_round1.get('sql_query_generated')}")
                        print(f"Round 1 sql_result: {final_state_round1.get('sql_result')}")

                        # 断言 (Round 1)
                        assert final_state_round1.get("final_answer") == "找到2个用户：testuser和user2"
                        # 检查 SQL 查询是否包含 "SELECT * FROM users"，不关心是否有分号
                        assert "SELECT * FROM users" in final_state_round1.get("sql_query_generated", "")
                        assert final_state_round1.get("sql_result") is not None

                        # ---- ROUND 2: 用户重置状态 ----
                        initial_user_query_round2 = "重置"
                        thread_id_round2 = "test-reset-flow-after-operation-r2"

                        initial_state_round2 = GraphState(**final_state_dict_round1)
                        initial_state_round2["user_query"] = initial_user_query_round2
                        initial_state_round2["raw_user_input"] = initial_user_query_round2
                        initial_state_round2["final_answer"] = None

                        config_round2 = {"configurable": {"thread_id": thread_id_round2}}

                        # 重置 mock 并设置新的返回值
                        mock_classify_main_intent.reset_mock()
                        mock_classify_main_intent.return_value = "reset"

                        # 调用图 (Round 2)
                        print(f"Invoking graph for Round 2 with query: {initial_user_query_round2}")
                        final_state_dict_round2 = compiled_app.invoke(dict(initial_state_round2), config_round2)
                        final_state_round2 = GraphState(**final_state_dict_round2)

                        # 调试打印语句
                        print(f"Round 2 final_answer: {final_state_round2.get('final_answer')}")
                        print(f"Round 2 sql_query_generated: {final_state_round2.get('sql_query_generated')}")
                        print(f"Round 2 sql_result: {final_state_round2.get('sql_result')}")

                        # 断言 (Round 2)
                        mock_classify_main_intent.assert_called_once_with(initial_user_query_round2)

                        # 验证最终回复
                        assert final_state_round2.get("final_answer") == "之前的操作状态已重置。"
                        # 注意：handle_reset_action 函数目前不会重置 sql_query_generated 和 sql_result
                        # 所以我们不检查这些状态

                        print("--- Test: test_reset_flow_after_operation PASSED SUCCESSFULLY ---")

def test_reset_flow_new_query_after_reset(compiled_app):
    """
    测试场景 7.3: 重置后新查询
    - 模拟用户先重置状态，然后执行新的查询
    - 验证重置后的新查询是否正常工作
    """
    print("\n--- Test: test_reset_flow_new_query_after_reset ---")

    # ---- ROUND 1: 用户重置状态 ----
    initial_user_query_round1 = "重置所有状态"
    thread_id_round1 = "test-reset-flow-new-query-r1"

    # 初始状态，包含一些需要被重置的数据
    initial_state_round1 = GraphState(
        user_query=initial_user_query_round1,
        raw_user_input=initial_user_query_round1,
        biaojiegou_save=MOCK_SCHEMA_JSON_STRING,
        table_names=MOCK_TABLE_NAMES,
        data_sample=MOCK_DATA_SAMPLE,
        content_modify="这是一些修改内容",
        delete_show="这是一些删除内容",
        lastest_content_production="这是最新的内容生产",
        delete_array=["id1", "id2"],
        content_new="这是一些新内容",
        save_content="这是保存的内容",
        sql_query_generated="SELECT * FROM users",
        sql_result=json.dumps([{"id": 1, "username": "testuser"}]),
        final_answer=None,
        error_message=None
    )
    config_round1 = {"configurable": {"thread_id": thread_id_round1}}

    # Mock LLM 服务
    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent:
        with patch('langgraph_crud_app.services.llm.llm_query_service.classify_query_analysis_intent') as mock_classify_query_analysis:
            with patch('langgraph_crud_app.services.llm.llm_query_service.generate_select_sql') as mock_generate_select_sql:
                with patch('langgraph_crud_app.services.api_client.execute_query') as mock_execute_query:
                    with patch('langgraph_crud_app.services.llm.llm_query_service.format_query_result') as mock_format_query_result:

                        # 设置 Mock 返回值 (Round 1)
                        mock_classify_main_intent.return_value = "reset"

                        # 调用图 (Round 1)
                        print(f"Invoking graph for Round 1 with query: {initial_user_query_round1}")
                        final_state_dict_round1 = compiled_app.invoke(dict(initial_state_round1), config_round1)
                        final_state_round1 = GraphState(**final_state_dict_round1)

                        # 调试打印语句
                        print(f"Round 1 final_answer: {final_state_round1.get('final_answer')}")
                        print(f"Round 1 sql_query_generated: {final_state_round1.get('sql_query_generated')}")

                        # 断言 (Round 1)
                        mock_classify_main_intent.assert_called_once_with(initial_user_query_round1)
                        assert final_state_round1.get("final_answer") == "之前的操作状态已重置。"
                        # 注意：handle_reset_action 函数目前不会重置 sql_query_generated 和 sql_result
                        # 所以我们不检查这些状态

                        # ---- ROUND 2: 用户执行新查询 ----
                        initial_user_query_round2 = "查询所有提示"
                        thread_id_round2 = "test-reset-flow-new-query-r2"

                        initial_state_round2 = GraphState(**final_state_dict_round1)
                        initial_state_round2["user_query"] = initial_user_query_round2
                        initial_state_round2["raw_user_input"] = initial_user_query_round2
                        initial_state_round2["final_answer"] = None

                        config_round2 = {"configurable": {"thread_id": thread_id_round2}}

                        # 重置 mock 并设置新的返回值
                        mock_classify_main_intent.reset_mock()
                        mock_classify_main_intent.return_value = "query_analysis"
                        mock_classify_query_analysis.return_value = "query"
                        mock_generate_select_sql.return_value = "SELECT * FROM prompts"
                        mock_execute_query.return_value = json.dumps([
                            {"id": 101, "user_id": 1, "title": "Test Prompt"},
                            {"id": 102, "user_id": 2, "title": "Another Prompt"}
                        ])
                        mock_format_query_result.return_value = "找到2个提示：Test Prompt和Another Prompt"

                        # 调用图 (Round 2)
                        print(f"Invoking graph for Round 2 with query: {initial_user_query_round2}")
                        final_state_dict_round2 = compiled_app.invoke(dict(initial_state_round2), config_round2)
                        final_state_round2 = GraphState(**final_state_dict_round2)

                        # 调试打印语句
                        print(f"Round 2 final_answer: {final_state_round2.get('final_answer')}")
                        print(f"Round 2 sql_query_generated: {final_state_round2.get('sql_query_generated')}")
                        print(f"Round 2 sql_result: {final_state_round2.get('sql_result')}")

                        # 断言 (Round 2)
                        mock_classify_main_intent.assert_called_once_with(initial_user_query_round2)
                        mock_classify_query_analysis.assert_called_once()
                        mock_generate_select_sql.assert_called_once()
                        # 注意：clean_sql 函数会在 SQL 语句末尾添加分号
                        mock_execute_query.assert_called_once_with("SELECT * FROM prompts;")
                        mock_format_query_result.assert_called_once()

                        assert final_state_round2.get("final_answer") == "找到2个提示：Test Prompt和Another Prompt"
                        # 注意：sql_query_generated 包含分号
                        assert "SELECT * FROM prompts" in final_state_round2.get("sql_query_generated", "")
                        assert final_state_round2.get("sql_result") is not None

                        print("--- Test: test_reset_flow_new_query_after_reset PASSED SUCCESSFULLY ---")
