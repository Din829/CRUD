"""
集成测试：复合流程
测试复合流程的各种场景，包括解析、占位符处理、预览和执行。
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
        "columns": {
            "id": {"type": "INTEGER", "primary_key": True, "autoincrement": True},
            "username": {"type": "VARCHAR(255)", "nullable": False},
            "email": {"type": "VARCHAR(255)", "nullable": False},
            "created_at": {"type": "TIMESTAMP", "nullable": True}
        }
    },
    "prompts": {
        "columns": {
            "id": {"type": "INTEGER", "primary_key": True, "autoincrement": True},
            "user_id": {"type": "INTEGER", "nullable": False, "foreign_key": "users.id"},
            "title": {"type": "VARCHAR(255)", "nullable": False},
            "content": {"type": "TEXT", "nullable": False},
            "category": {"type": "VARCHAR(50)", "nullable": True},
            "created_at": {"type": "TIMESTAMP", "nullable": True},
            "updated_at": {"type": "TIMESTAMP", "nullable": True}
        }
    }
})

MOCK_TABLE_NAMES = ["users", "prompts"]

MOCK_DATA_SAMPLE = json.dumps({
    "users": [{"id": 1, "username": "testuser", "email": "test@example.com", "created_at": "2023-01-01 00:00:00"}],
    "prompts": [{"id": 1, "user_id": 1, "title": "Test Prompt", "content": "This is a test prompt", "category": "test", "created_at": "2023-01-01 00:00:00", "updated_at": "2023-01-01 00:00:00"}]
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


def test_composite_simple_success(compiled_app):
    """
    测试 6.1: 简单复合操作，成功完成整个流程。
    包括解析复合请求、处理占位符、格式化预览、
    首次确认（保存）、最终确认（是）和API调用。
    """
    print("\n--- Test: test_composite_simple_success ---")

    # ---- ROUND 1: 用户发起复合请求，系统解析、处理占位符并返回预览 ----
    initial_user_query_round1 = "为用户testuser创建一个提示，标题是'周报'，内容是'本周工作总结'，类别是'work'，然后将类别改为'report'"
    thread_id_round1 = "test-composite-simple-thread-r1"

    initial_state_round1 = GraphState(
        user_query=initial_user_query_round1,
        raw_user_input=initial_user_query_round1,
        biaojiegou_save=MOCK_SCHEMA_JSON_STRING,
        table_names=MOCK_TABLE_NAMES,
        data_sample=MOCK_DATA_SAMPLE,
        final_answer=None, error_message=None, raw_schema_result=None, raw_table_names_str=None,
        sql_query_generated=None, sql_result=None, main_intent=None, query_analysis_intent=None,
        modify_context_sql=None, modify_context_result=None, raw_modify_llm_output=None, modify_error_message=None,
        temp_add_llm_data=None, add_structured_records_str=None, structured_add_records=None,
        add_processed_records_str=None, add_processed_records=None, add_preview_text=None, add_error_message=None,
        combined_operation_plan=None, content_combined=None,
        content_modify=None, content_new=None, delete_show=None, lastest_content_production=None,
        delete_array=None, save_content=None, api_call_result=None, add_parse_error=None,
        delete_preview_sql=None, delete_preview_text=None, delete_error_message=None,
        delete_ids_llm_output=None, delete_ids_structured_str=None, delete_show_json=None
    )
    initial_state_dict_round1 = dict(initial_state_round1)
    config_round1 = {"configurable": {"thread_id": thread_id_round1}}

    # Mock LLM 服务和 API 调用
    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent:
        with patch('langgraph_crud_app.services.llm.llm_composite_service.parse_combined_request') as mock_parse_combined_request:
            with patch('langgraph_crud_app.services.api_client.execute_query') as mock_execute_query:
                with patch('langgraph_crud_app.services.llm.llm_composite_service.format_combined_preview') as mock_format_combined_preview:

                    # 设置 Mock 返回值 (Round 1)
                    mock_classify_main_intent.return_value = {"intent": "composite", "confidence": 0.98}

                    # 模拟解析复合请求的结果
                    mock_combined_plan = [
                        {
                            "operation": "insert",
                            "table_name": "prompts",
                            "values": {
                                "user_id": "{{db(SELECT id FROM users WHERE username = 'testuser')}}",
                                "title": "周报",
                                "content": "本周工作总结",
                                "category": "work",
                                "created_at": "now()",
                                "updated_at": "now()"
                            },
                            "return_affected": ["id"]
                        },
                        {
                            "operation": "update",
                            "table_name": "prompts",
                            "where": {
                                "id": "{{previous_result[0].id}}"
                            },
                            "set": {
                                "category": "report",
                                "updated_at": "now()"
                            },
                            "depends_on_index": 0
                        }
                    ]
                    mock_parse_combined_request.return_value = mock_combined_plan

                    # 模拟数据库查询结果
                    mock_execute_query.return_value = json.dumps([{"id": 1}])  # 模拟查询用户ID的结果

                    # 模拟格式化预览的结果
                    expected_preview_text = """我将执行以下复合操作：

1. 新增：在prompts表中创建一条新记录，标题为"周报"，内容为"本周工作总结"，类别为"work"，关联到用户"testuser"。
2. 更新：将刚创建的提示记录的类别从"work"修改为"report"。

请确认是否执行这些操作？"""
                    mock_format_combined_preview.return_value = expected_preview_text

                    # 调用图 (Round 1)
                    print(f"Invoking graph for Round 1 with query: {initial_user_query_round1}")
                    final_state_dict_round1 = compiled_app.invoke(initial_state_dict_round1, config_round1)
                    final_state_round1 = GraphState(**final_state_dict_round1)

                    # 调试打印语句
                    r1_final_answer = final_state_round1.get('final_answer')
                    r1_error_message = final_state_round1.get('error_message')
                    r1_combined_plan = final_state_round1.get('combined_operation_plan')
                    r1_content_combined = final_state_round1.get('content_combined')
                    print(f"Round 1 final_answer: {r1_final_answer}")
                    print(f"Round 1 error_message: {r1_error_message}")
                    print(f"Round 1 combined_operation_plan: {r1_combined_plan}")
                    print(f"Round 1 content_combined: {r1_content_combined}")

                    # 断言 (Round 1)
                    mock_classify_main_intent.assert_called_once_with(initial_user_query_round1)
                    mock_parse_combined_request.assert_called_once_with(
                        user_query=initial_user_query_round1,
                        schema_info=MOCK_SCHEMA_JSON_STRING,
                        table_names=MOCK_TABLE_NAMES,
                        sample_data=MOCK_DATA_SAMPLE
                    )
                    mock_execute_query.assert_called_once_with("SELECT id FROM users WHERE username = 'testuser'")
                    mock_format_combined_preview.assert_called_once_with(
                        user_query=initial_user_query_round1,
                        combined_operation_plan=mock_combined_plan
                    )

                    # 验证状态
                    assert final_state_round1.get("combined_operation_plan") == mock_combined_plan
                    assert final_state_round1.get("content_combined") == expected_preview_text
                    assert final_state_round1.get("error_message") is None
                    assert "以下是即将执行的【复合操作】" in final_state_round1.get("final_answer", "")
                    assert "请确认" in final_state_round1.get("final_answer", "")
                    assert final_state_round1.get("save_content") == "复合路径"

                    print(f"test_composite_simple_success - Round 1 PASSED (User query: {initial_user_query_round1})")

                    # ---- ROUND 2: 用户输入 "是"，系统执行复合操作并返回成功信息 ----
                    initial_user_query_round2 = "是"
                    thread_id_round2 = "test-composite-simple-thread-r2"

                    initial_state_round2 = GraphState(**final_state_dict_round1)
                    initial_state_round2["user_query"] = initial_user_query_round2
                    initial_state_round2["raw_user_input"] = initial_user_query_round2
                    initial_state_round2["final_answer"] = None
                    initial_state_round2["error_message"] = None

                    initial_state_dict_round2 = dict(initial_state_round2)
                    config_round2 = {"configurable": {"thread_id": thread_id_round2}}

                    # 为 Round 2 设置新的 Mock
                    with patch('langgraph_crud_app.services.llm.llm_flow_control_service.classify_yes_no') as mock_classify_yes_no:
                        with patch('langgraph_crud_app.services.api_client.execute_batch_operations') as mock_execute_batch_operations:
                            with patch('langgraph_crud_app.services.llm.llm_flow_control_service.format_api_result') as mock_format_api_result:

                                mock_classify_main_intent.reset_mock()
                                mock_classify_main_intent.return_value = {"intent": "confirm_other", "confidence": 0.99}
                                mock_classify_yes_no.return_value = "yes"

                                # 模拟批量操作的结果
                                mock_api_response_success = {
                                    "message": "Batch operations executed successfully.",
                                    "results": [
                                        {
                                            "success": True,
                                            "operation_index": 0,
                                            "operation_type": "insert",
                                            "table_name": "prompts",
                                            "affected_rows": 1,
                                            "last_insert_id": 2
                                        },
                                        {
                                            "success": True,
                                            "operation_index": 1,
                                            "operation_type": "update",
                                            "table_name": "prompts",
                                            "affected_rows": 1
                                        }
                                    ]
                                }
                                mock_execute_batch_operations.return_value = mock_api_response_success

                                expected_final_success_message = "复合操作成功完成。已创建新提示'周报'并将其类别更新为'report'。"
                                mock_format_api_result.return_value = expected_final_success_message

                                # 调用图 (Round 2)
                                print(f"Invoking graph for Round 2 with query: {initial_user_query_round2}")
                                final_state_dict_round2 = compiled_app.invoke(initial_state_dict_round2, config_round2)
                                final_state_round2 = GraphState(**final_state_dict_round2)
                                print(f"Round 2 final_answer: {final_state_round2.get('final_answer')}")
                                print(f"Round 2 error_message: {final_state_round2.get('error_message')}")
                                print(f"Round 2 api_call_result: {final_state_round2.get('api_call_result')}")

                                # 断言 (Round 2)
                                mock_classify_main_intent.assert_called_once_with(initial_user_query_round2)
                                mock_classify_yes_no.assert_called_once_with(initial_user_query_round2)
                                mock_execute_batch_operations.assert_called_once()

                                # 验证 format_api_result 调用
                                assert mock_format_api_result.call_count == 1
                                _, kwargs = mock_format_api_result.call_args
                                assert kwargs.get("original_query") == initial_user_query_round2

                                # 验证最终状态
                                assert final_state_round2.get("final_answer") == expected_final_success_message
                                assert final_state_round2.get("error_message") is None
                                assert final_state_round2.get("save_content") is None  # 操作后应该被清空
                                assert final_state_round2.get("combined_operation_plan") is None  # 操作后应该被清空
                                assert final_state_round2.get("content_combined") is None  # 操作后应该被清空
                                assert final_state_round2.get("lastest_content_production") is None  # 操作后应该被清空

                                print(f"test_composite_simple_success - Round 2 PASSED (User query: {initial_user_query_round2})")
                                print("--- Test: test_composite_simple_success PASSED SUCCESSFULLY ---")


def test_composite_db_placeholder_empty_result(compiled_app):
    """
    测试 6.2: {{db()}} 查询返回空列表，导致某个 insert 操作的 user_id 解析为 []。
    验证系统是否正确处理这种情况，过滤掉无效的 insert 操作，并向用户提供适当的反馈。
    """
    print("\n--- Test: test_composite_db_placeholder_empty_result ---")

    # ---- ROUND 1: 用户发起复合请求，但 {{db()}} 查询返回空列表 ----
    initial_user_query_round1 = "为用户nonexistent创建一个提示，标题是'周报'，内容是'本周工作总结'，类别是'work'"
    thread_id_round1 = "test-composite-empty-db-thread-r1"

    initial_state_round1 = GraphState(
        user_query=initial_user_query_round1,
        raw_user_input=initial_user_query_round1,
        biaojiegou_save=MOCK_SCHEMA_JSON_STRING,
        table_names=MOCK_TABLE_NAMES,
        data_sample=MOCK_DATA_SAMPLE,
        final_answer=None, error_message=None, raw_schema_result=None, raw_table_names_str=None,
        sql_query_generated=None, sql_result=None, main_intent=None, query_analysis_intent=None,
        modify_context_sql=None, modify_context_result=None, raw_modify_llm_output=None, modify_error_message=None,
        temp_add_llm_data=None, add_structured_records_str=None, structured_add_records=None,
        add_processed_records_str=None, add_processed_records=None, add_preview_text=None, add_error_message=None,
        combined_operation_plan=None, content_combined=None,
        content_modify=None, content_new=None, delete_show=None, lastest_content_production=None,
        delete_array=None, save_content=None, api_call_result=None, add_parse_error=None,
        delete_preview_sql=None, delete_preview_text=None, delete_error_message=None,
        delete_ids_llm_output=None, delete_ids_structured_str=None, delete_show_json=None
    )
    initial_state_dict_round1 = dict(initial_state_round1)
    config_round1 = {"configurable": {"thread_id": thread_id_round1}}

    # Mock LLM 服务和 API 调用
    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent:
        with patch('langgraph_crud_app.services.llm.llm_composite_service.parse_combined_request') as mock_parse_combined_request:
            with patch('langgraph_crud_app.services.api_client.execute_query') as mock_execute_query:
                with patch('langgraph_crud_app.services.llm.llm_composite_service.format_combined_preview') as mock_format_combined_preview:

                    # 设置 Mock 返回值 (Round 1)
                    mock_classify_main_intent.return_value = {"intent": "composite", "confidence": 0.98}

                    # 模拟解析复合请求的结果
                    mock_combined_plan = [
                        {
                            "operation": "insert",
                            "table_name": "prompts",
                            "values": {
                                "user_id": "{{db(SELECT id FROM users WHERE username = 'nonexistent')}}",
                                "title": "周报",
                                "content": "本周工作总结",
                                "category": "work",
                                "created_at": "now()",
                                "updated_at": "now()"
                            }
                        }
                    ]
                    mock_parse_combined_request.return_value = mock_combined_plan

                    # 关键点：模拟数据库查询返回空结果
                    mock_execute_query.return_value = "[]"  # 空列表，表示没有找到用户

                    # 模拟格式化预览的结果
                    expected_preview_text = """无法执行您的请求。

原因：找不到用户名为"nonexistent"的用户。请确认用户名是否正确，或者先创建该用户。

技术细节：在处理复合操作时，系统尝试查找用户ID（通过查询"SELECT id FROM users WHERE username = 'nonexistent'"），但未找到匹配记录。"""
                    mock_format_combined_preview.return_value = expected_preview_text

                    # 调用图 (Round 1)
                    print(f"Invoking graph for Round 1 with query: {initial_user_query_round1}")
                    final_state_dict_round1 = compiled_app.invoke(initial_state_dict_round1, config_round1)
                    final_state_round1 = GraphState(**final_state_dict_round1)

                    # 调试打印语句
                    r1_final_answer = final_state_round1.get('final_answer')
                    r1_error_message = final_state_round1.get('error_message')
                    r1_combined_plan = final_state_round1.get('combined_operation_plan')
                    r1_content_combined = final_state_round1.get('content_combined')
                    r1_lastest_content_production = final_state_round1.get('lastest_content_production')
                    print(f"Round 1 final_answer: {r1_final_answer}")
                    print(f"Round 1 error_message: {r1_error_message}")
                    print(f"Round 1 combined_operation_plan: {r1_combined_plan}")
                    print(f"Round 1 content_combined: {r1_content_combined}")
                    print(f"Round 1 lastest_content_production: {r1_lastest_content_production}")

                    # 断言 (Round 1)
                    mock_classify_main_intent.assert_called_once_with(initial_user_query_round1)
                    mock_parse_combined_request.assert_called_once_with(
                        user_query=initial_user_query_round1,
                        schema_info=MOCK_SCHEMA_JSON_STRING,
                        table_names=MOCK_TABLE_NAMES,
                        sample_data=MOCK_DATA_SAMPLE
                    )
                    mock_execute_query.assert_called_once_with("SELECT id FROM users WHERE username = 'nonexistent'")
                    mock_format_combined_preview.assert_called_once()

                    # 验证状态
                    assert final_state_round1.get("combined_operation_plan") == mock_combined_plan
                    assert final_state_round1.get("content_combined") == expected_preview_text

                    # 关键点：验证 lastest_content_production 是空列表，表示所有操作都被过滤掉了
                    assert final_state_round1.get("lastest_content_production") == []

                    # 验证错误消息
                    assert final_state_round1.get("error_message") == "无法暂存复合操作，缺少必要内容。"

                    # 验证没有设置 save_content，因为不应进入确认流程
                    assert final_state_round1.get("save_content") is None

                    print("--- Test: test_composite_db_placeholder_empty_result PASSED SUCCESSFULLY ---")


def test_composite_db_placeholder_multiple_ids(compiled_app):
    """
    测试 6.3: {{db()}} 查询返回多个ID，用于 UPDATE ... WHERE id IN {{db()}}。
    验证 process_composite_placeholders_action 和 _process_value 是否将列表正确传递，
    并由后端 /execute_batch_operations 正确处理 IN (...)。
    """
    print("\n--- Test: test_composite_db_placeholder_multiple_ids ---")

    # ---- ROUND 1: 用户发起复合请求，{{db()}} 查询返回多个ID ----
    initial_user_query_round1 = "将所有用户的提示类别改为'updated'"
    thread_id_round1 = "test-composite-multiple-ids-thread-r1"

    initial_state_round1 = GraphState(
        user_query=initial_user_query_round1,
        raw_user_input=initial_user_query_round1,
        biaojiegou_save=MOCK_SCHEMA_JSON_STRING,
        table_names=MOCK_TABLE_NAMES,
        data_sample=MOCK_DATA_SAMPLE,
        final_answer=None, error_message=None, raw_schema_result=None, raw_table_names_str=None,
        sql_query_generated=None, sql_result=None, main_intent=None, query_analysis_intent=None,
        modify_context_sql=None, modify_context_result=None, raw_modify_llm_output=None, modify_error_message=None,
        temp_add_llm_data=None, add_structured_records_str=None, structured_add_records=None,
        add_processed_records_str=None, add_processed_records=None, add_preview_text=None, add_error_message=None,
        combined_operation_plan=None, content_combined=None,
        content_modify=None, content_new=None, delete_show=None, lastest_content_production=None,
        delete_array=None, save_content=None, api_call_result=None, add_parse_error=None,
        delete_preview_sql=None, delete_preview_text=None, delete_error_message=None,
        delete_ids_llm_output=None, delete_ids_structured_str=None, delete_show_json=None
    )
    initial_state_dict_round1 = dict(initial_state_round1)
    config_round1 = {"configurable": {"thread_id": thread_id_round1}}

    # Mock LLM 服务和 API 调用
    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent:
        with patch('langgraph_crud_app.services.llm.llm_composite_service.parse_combined_request') as mock_parse_combined_request:
            with patch('langgraph_crud_app.services.api_client.execute_query') as mock_execute_query:
                with patch('langgraph_crud_app.services.llm.llm_composite_service.format_combined_preview') as mock_format_combined_preview:

                    # 设置 Mock 返回值 (Round 1)
                    mock_classify_main_intent.return_value = {"intent": "composite", "confidence": 0.98}

                    # 模拟解析复合请求的结果
                    mock_combined_plan = [
                        {
                            "operation": "update",
                            "table_name": "prompts",
                            "where": {
                                "user_id": {"IN": "{{db(SELECT id FROM users)}}"}
                            },
                            "set": {
                                "category": "updated",
                                "updated_at": "now()"
                            }
                        }
                    ]
                    mock_parse_combined_request.return_value = mock_combined_plan

                    # 关键点：模拟数据库查询返回多个ID
                    mock_execute_query.return_value = json.dumps([
                        {"id": 1},
                        {"id": 2},
                        {"id": 3}
                    ])

                    # 模拟格式化预览的结果
                    expected_preview_text = """我将执行以下操作：

更新：将所有用户（ID为1、2、3）的提示类别改为"updated"，并更新修改时间。

请确认是否执行这些操作？"""
                    mock_format_combined_preview.return_value = expected_preview_text

                    # 调用图 (Round 1)
                    print(f"Invoking graph for Round 1 with query: {initial_user_query_round1}")
                    final_state_dict_round1 = compiled_app.invoke(initial_state_dict_round1, config_round1)
                    final_state_round1 = GraphState(**final_state_dict_round1)

                    # 调试打印语句
                    r1_final_answer = final_state_round1.get('final_answer')
                    r1_error_message = final_state_round1.get('error_message')
                    r1_combined_plan = final_state_round1.get('combined_operation_plan')
                    r1_content_combined = final_state_round1.get('content_combined')
                    r1_lastest_content_production = final_state_round1.get('lastest_content_production')
                    print(f"Round 1 final_answer: {r1_final_answer}")
                    print(f"Round 1 error_message: {r1_error_message}")
                    print(f"Round 1 combined_operation_plan: {r1_combined_plan}")
                    print(f"Round 1 content_combined: {r1_content_combined}")
                    print(f"Round 1 lastest_content_production: {r1_lastest_content_production}")

                    # 断言 (Round 1)
                    mock_classify_main_intent.assert_called_once_with(initial_user_query_round1)
                    mock_parse_combined_request.assert_called_once_with(
                        user_query=initial_user_query_round1,
                        schema_info=MOCK_SCHEMA_JSON_STRING,
                        table_names=MOCK_TABLE_NAMES,
                        sample_data=MOCK_DATA_SAMPLE
                    )
                    mock_execute_query.assert_called_once_with("SELECT id FROM users")
                    mock_format_combined_preview.assert_called_once()

                    # 验证状态
                    assert final_state_round1.get("combined_operation_plan") == mock_combined_plan
                    assert final_state_round1.get("content_combined") == expected_preview_text
                    assert final_state_round1.get("error_message") is None

                    # 关键点：验证 lastest_content_production 中的 where 子句已正确处理
                    processed_plan = final_state_round1.get("lastest_content_production")
                    assert len(processed_plan) == 1
                    assert processed_plan[0]["operation"] == "update"
                    assert processed_plan[0]["table_name"] == "prompts"
                    assert processed_plan[0]["set"]["category"] == "updated"

                    # 验证 where 子句中的 IN 操作符已正确处理
                    assert "IN" in processed_plan[0]["where"]["user_id"]
                    assert processed_plan[0]["where"]["user_id"]["IN"] == [1, 2, 3]

                    # 验证最终回复包含了预览信息
                    assert "将所有用户" in final_state_round1.get("final_answer", "")
                    assert "请确认" in final_state_round1.get("final_answer", "")
                    assert "回复'是'/'否'" in final_state_round1.get("final_answer", "")

                    # ---- ROUND 2: 用户输入 "是"，系统执行操作 ----
                    initial_user_query_round2 = "是"
                    thread_id_round2 = "test-composite-multiple-ids-thread-r2"

                    initial_state_round2 = GraphState(**final_state_dict_round1)
                    initial_state_round2["user_query"] = initial_user_query_round2
                    initial_state_round2["raw_user_input"] = initial_user_query_round2
                    initial_state_round2["final_answer"] = None
                    initial_state_round2["error_message"] = None

                    initial_state_dict_round2 = dict(initial_state_round2)
                    config_round2 = {"configurable": {"thread_id": thread_id_round2}}

                    # 为 Round 2 设置新的 Mock
                    with patch('langgraph_crud_app.services.llm.llm_flow_control_service.classify_yes_no') as mock_classify_yes_no:
                        with patch('langgraph_crud_app.services.api_client.execute_batch_operations') as mock_execute_batch_operations:
                            with patch('langgraph_crud_app.services.llm.llm_flow_control_service.format_api_result') as mock_format_api_result:

                                mock_classify_main_intent.reset_mock()
                                mock_classify_main_intent.return_value = {"intent": "confirm_other", "confidence": 0.99}
                                mock_classify_yes_no.return_value = "yes"

                                # 模拟批量操作的结果
                                mock_api_response_success = {
                                    "message": "Batch operations executed successfully.",
                                    "results": [
                                        {
                                            "success": True,
                                            "operation_index": 0,
                                            "operation_type": "update",
                                            "table_name": "prompts",
                                            "affected_rows": 3
                                        }
                                    ]
                                }
                                mock_execute_batch_operations.return_value = mock_api_response_success

                                expected_final_success_message = "复合操作成功完成。已更新3条提示记录的类别为'updated'。"
                                mock_format_api_result.return_value = expected_final_success_message

                                # 调用图 (Round 2)
                                print(f"Invoking graph for Round 2 with query: {initial_user_query_round2}")
                                final_state_dict_round2 = compiled_app.invoke(initial_state_dict_round2, config_round2)
                                final_state_round2 = GraphState(**final_state_dict_round2)
                                print(f"Round 2 final_answer: {final_state_round2.get('final_answer')}")
                                print(f"Round 2 error_message: {final_state_round2.get('error_message')}")
                                print(f"Round 2 api_call_result: {final_state_round2.get('api_call_result')}")

                                # 断言 (Round 2)
                                mock_classify_main_intent.assert_called_once_with(initial_user_query_round2)
                                mock_classify_yes_no.assert_called_once_with(initial_user_query_round2)

                                # 验证 execute_batch_operations 调用
                                mock_execute_batch_operations.assert_called_once()
                                args, _ = mock_execute_batch_operations.call_args
                                batch_operations = args[0]

                                # 验证传递给 execute_batch_operations 的参数
                                assert len(batch_operations) == 1
                                assert batch_operations[0]["operation"] == "update"
                                assert batch_operations[0]["table_name"] == "prompts"
                                assert batch_operations[0]["set"]["category"] == "updated"
                                assert "IN" in batch_operations[0]["where"]["user_id"]
                                assert batch_operations[0]["where"]["user_id"]["IN"] == [1, 2, 3]

                                # 验证 format_api_result 调用
                                assert mock_format_api_result.call_count == 1
                                _, kwargs = mock_format_api_result.call_args
                                assert kwargs.get("original_query") == initial_user_query_round2

                                # 验证最终状态
                                assert final_state_round2.get("final_answer") == expected_final_success_message
                                assert final_state_round2.get("error_message") is None
                                assert final_state_round2.get("save_content") is None  # 操作后应该被清空
                                assert final_state_round2.get("combined_operation_plan") is None  # 操作后应该被清空
                                assert final_state_round2.get("content_combined") is None  # 操作后应该被清空
                                assert final_state_round2.get("lastest_content_production") is None  # 操作后应该被清空

                                print(f"test_composite_db_placeholder_multiple_ids - Round 2 PASSED (User query: {initial_user_query_round2})")
                                print("--- Test: test_composite_db_placeholder_multiple_ids PASSED SUCCESSFULLY ---")


def test_composite_placeholder_processing_failure(compiled_app):
    """
    测试 6.4: 占位符解析失败。
    验证 process_composite_placeholders_action 的错误处理。
    """
    print("\n--- Test: test_composite_placeholder_processing_failure ---")

    # ---- ROUND 1: 用户发起复合请求，但占位符解析失败 ----
    initial_user_query_round1 = "为用户testuser创建一个提示，标题是'周报'，内容是'本周工作总结'，类别是'work'，然后将类别改为'report'"
    thread_id_round1 = "test-composite-placeholder-fail-thread-r1"

    initial_state_round1 = GraphState(
        user_query=initial_user_query_round1,
        raw_user_input=initial_user_query_round1,
        biaojiegou_save=MOCK_SCHEMA_JSON_STRING,
        table_names=MOCK_TABLE_NAMES,
        data_sample=MOCK_DATA_SAMPLE,
        final_answer=None, error_message=None, raw_schema_result=None, raw_table_names_str=None,
        sql_query_generated=None, sql_result=None, main_intent=None, query_analysis_intent=None,
        modify_context_sql=None, modify_context_result=None, raw_modify_llm_output=None, modify_error_message=None,
        temp_add_llm_data=None, add_structured_records_str=None, structured_add_records=None,
        add_processed_records_str=None, add_processed_records=None, add_preview_text=None, add_error_message=None,
        combined_operation_plan=None, content_combined=None,
        content_modify=None, content_new=None, delete_show=None, lastest_content_production=None,
        delete_array=None, save_content=None, api_call_result=None, add_parse_error=None,
        delete_preview_sql=None, delete_preview_text=None, delete_error_message=None,
        delete_ids_llm_output=None, delete_ids_structured_str=None, delete_show_json=None
    )
    initial_state_dict_round1 = dict(initial_state_round1)
    config_round1 = {"configurable": {"thread_id": thread_id_round1}}

    # Mock LLM 服务和 API 调用
    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent:
        with patch('langgraph_crud_app.services.llm.llm_composite_service.parse_combined_request') as mock_parse_combined_request:
            with patch('langgraph_crud_app.services.api_client.execute_query') as mock_execute_query:
                with patch('langgraph_crud_app.services.llm.llm_composite_service.format_combined_preview') as mock_format_combined_preview:

                    # 设置 Mock 返回值 (Round 1)
                    mock_classify_main_intent.return_value = {"intent": "composite", "confidence": 0.98}

                    # 模拟解析复合请求的结果
                    mock_combined_plan = [
                        {
                            "operation": "insert",
                            "table_name": "prompts",
                            "values": {
                                "user_id": "{{db(SELECT id FROM users WHERE username = 'testuser')}}",
                                "title": "周报",
                                "content": "本周工作总结",
                                "category": "work",
                                "created_at": "now()",
                                "updated_at": "now()"
                            },
                            "return_affected": ["id"]
                        },
                        {
                            "operation": "update",
                            "table_name": "prompts",
                            "where": {
                                "id": "{{previous_result[0].id}}"
                            },
                            "set": {
                                "category": "report",
                                "updated_at": "now()"
                            },
                            "depends_on_index": 0
                        }
                    ]
                    mock_parse_combined_request.return_value = mock_combined_plan

                    # 关键点：模拟数据库查询抛出异常
                    mock_execute_query.side_effect = ValueError("数据库查询执行失败：语法错误")

                    # 调用图 (Round 1)
                    print(f"Invoking graph for Round 1 with query: {initial_user_query_round1}")
                    final_state_dict_round1 = compiled_app.invoke(initial_state_dict_round1, config_round1)
                    final_state_round1 = GraphState(**final_state_dict_round1)

                    # 调试打印语句
                    r1_final_answer = final_state_round1.get('final_answer')
                    r1_error_message = final_state_round1.get('error_message')
                    r1_combined_plan = final_state_round1.get('combined_operation_plan')
                    r1_content_combined = final_state_round1.get('content_combined')
                    r1_lastest_content_production = final_state_round1.get('lastest_content_production')
                    print(f"Round 1 final_answer: {r1_final_answer}")
                    print(f"Round 1 error_message: {r1_error_message}")
                    print(f"Round 1 combined_operation_plan: {r1_combined_plan}")
                    print(f"Round 1 content_combined: {r1_content_combined}")
                    print(f"Round 1 lastest_content_production: {r1_lastest_content_production}")

                    # 断言 (Round 1)
                    mock_classify_main_intent.assert_called_once_with(initial_user_query_round1)
                    mock_parse_combined_request.assert_called_once_with(
                        user_query=initial_user_query_round1,
                        schema_info=MOCK_SCHEMA_JSON_STRING,
                        table_names=MOCK_TABLE_NAMES,
                        sample_data=MOCK_DATA_SAMPLE
                    )
                    mock_execute_query.assert_called_once_with("SELECT id FROM users WHERE username = 'testuser'")

                    # 即使占位符处理失败，format_combined_preview 仍然会被调用
                    # 但它的结果不会被使用，因为 lastest_content_production 为 None

                    # 验证状态
                    assert final_state_round1.get("combined_operation_plan") == mock_combined_plan

                    # 关键点：验证错误消息和 lastest_content_production 为 None
                    assert final_state_round1.get("error_message") == "无法暂存复合操作，缺少必要内容。"
                    assert final_state_round1.get("lastest_content_production") is None

                    # 验证没有设置 save_content，因为不应进入确认流程
                    assert final_state_round1.get("save_content") is None

                    # 验证最终回复为 None，因为错误消息已经设置在 error_message 中
                    assert final_state_round1.get("final_answer") is None

                    print("--- Test: test_composite_placeholder_processing_failure PASSED SUCCESSFULLY ---")


def test_composite_llm_parsing_failure(compiled_app):
    """
    测试 6.5: LLM 解析复合请求失败。
    验证 parse_combined_request_action 的错误处理。
    """
    print("\n--- Test: test_composite_llm_parsing_failure ---")

    # ---- ROUND 1: 用户发起复合请求，但LLM解析失败 ----
    initial_user_query_round1 = "为所有用户更新邮箱，然后添加一个新的提示"
    thread_id_round1 = "test-composite-llm-parsing-fail-thread-r1"

    initial_state_round1 = GraphState(
        user_query=initial_user_query_round1,
        raw_user_input=initial_user_query_round1,
        biaojiegou_save=MOCK_SCHEMA_JSON_STRING,
        table_names=MOCK_TABLE_NAMES,
        data_sample=MOCK_DATA_SAMPLE,
        final_answer=None, error_message=None, raw_schema_result=None, raw_table_names_str=None,
        sql_query_generated=None, sql_result=None, main_intent=None, query_analysis_intent=None,
        modify_context_sql=None, modify_context_result=None, raw_modify_llm_output=None, modify_error_message=None,
        temp_add_llm_data=None, add_structured_records_str=None, structured_add_records=None,
        add_processed_records_str=None, add_processed_records=None, add_preview_text=None, add_error_message=None,
        combined_operation_plan=None, content_combined=None,
        content_modify=None, content_new=None, delete_show=None, lastest_content_production=None,
        delete_array=None, save_content=None, api_call_result=None, add_parse_error=None,
        delete_preview_sql=None, delete_preview_text=None, delete_error_message=None,
        delete_ids_llm_output=None, delete_ids_structured_str=None, delete_show_json=None
    )
    initial_state_dict_round1 = dict(initial_state_round1)
    config_round1 = {"configurable": {"thread_id": thread_id_round1}}

    # Mock LLM 服务和 API 调用
    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent:
        with patch('langgraph_crud_app.services.llm.llm_composite_service.parse_combined_request') as mock_parse_combined_request:
            with patch('langgraph_crud_app.services.api_client.execute_query') as mock_execute_query:
                with patch('langgraph_crud_app.services.llm.llm_composite_service.format_combined_preview') as mock_format_combined_preview:

                    # 设置 Mock 返回值 (Round 1)
                    mock_classify_main_intent.return_value = {"intent": "composite", "confidence": 0.98}

                    # 关键点：模拟LLM解析失败
                    mock_parse_combined_request.side_effect = ValueError("无法解析复合请求：请求过于模糊或不完整")

                    # 调用图 (Round 1)
                    print(f"Invoking graph for Round 1 with query: {initial_user_query_round1}")
                    final_state_dict_round1 = compiled_app.invoke(initial_state_dict_round1, config_round1)
                    final_state_round1 = GraphState(**final_state_dict_round1)

                    # 调试打印语句
                    r1_final_answer = final_state_round1.get('final_answer')
                    r1_error_message = final_state_round1.get('error_message')
                    r1_combined_plan = final_state_round1.get('combined_operation_plan')
                    r1_content_combined = final_state_round1.get('content_combined')
                    r1_lastest_content_production = final_state_round1.get('lastest_content_production')
                    print(f"Round 1 final_answer: {r1_final_answer}")
                    print(f"Round 1 error_message: {r1_error_message}")
                    print(f"Round 1 combined_operation_plan: {r1_combined_plan}")
                    print(f"Round 1 content_combined: {r1_content_combined}")
                    print(f"Round 1 lastest_content_production: {r1_lastest_content_production}")

                    # 断言 (Round 1)
                    mock_classify_main_intent.assert_called_once_with(initial_user_query_round1)
                    mock_parse_combined_request.assert_called_once_with(
                        user_query=initial_user_query_round1,
                        schema_info=MOCK_SCHEMA_JSON_STRING,
                        table_names=MOCK_TABLE_NAMES,
                        sample_data=MOCK_DATA_SAMPLE
                    )

                    # 验证 execute_query 和 format_combined_preview 没有被调用
                    mock_execute_query.assert_not_called()
                    mock_format_combined_preview.assert_not_called()

                    # 验证状态
                    assert final_state_round1.get("combined_operation_plan") is None
                    assert final_state_round1.get("lastest_content_production") == []

                    # 关键点：验证错误消息
                    assert "无法暂存复合操作，缺少必要内容。" == final_state_round1.get("error_message", "")

                    # 验证最终回复为 None，因为错误消息已经设置在 error_message 中
                    assert final_state_round1.get("final_answer") is None

                    # 验证没有设置 save_content，因为不应进入确认流程
                    assert final_state_round1.get("save_content") is None

                    print("--- Test: test_composite_llm_parsing_failure PASSED SUCCESSFULLY ---")
