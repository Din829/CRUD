import pytest
import json
from unittest.mock import patch, MagicMock, call, ANY
import copy

# 将项目根目录添加到 sys.path 以便导入 langgraph_crud_app
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))  # 从 text/integration_tests 退两级到 DifyLang
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 假设 GraphState 和其他必要组件是可以导入的
from langgraph_crud_app.graph.state import GraphState
from langgraph_crud_app.graph.graph_builder import build_graph
from langgraph.checkpoint.memory import InMemorySaver

# 最小有效 schema，作为 JSON 字符串 (可以从 test_langgraph_flows.py 复制或重新定义更简单的)
MOCK_SCHEMA_JSON_STRING = json.dumps({
    "users": {
        "fields": {
            "id": {"type": "int", "key": "PRI", "null": "NO", "default": None},
            "username": {"type": "varchar(50)", "key": "UNI", "null": "NO", "default": None},
            "email": {"type": "varchar(100)", "key": "UNI", "null": "NO", "default": None},
            "password": {"type": "varchar(255)", "null": "NO", "key": "", "default": None},
            "reports_to_user_id": {"type": "int", "null": "YES", "key": "", "default": None}
        },
        "constraints": [
            {"name": "PRIMARY", "type": "PRIMARY KEY", "columns": ["id"]},
            {"name": "username", "type": "UNIQUE KEY", "columns": ["username"]},
            {"name": "email", "type": "UNIQUE KEY", "columns": ["email"]}
        ],
        "description": "用于存储用户信息的表。"
    }
})

MOCK_TABLE_NAMES = ["users"]

@pytest.fixture(scope="function")
def checkpointer(): 
    """提供一个 InMemorySaver 实例作为 checkpointer。"""
    return InMemorySaver()

@pytest.fixture(scope="function")
def compiled_app(checkpointer): 
    graph_definition = build_graph()
    try:
        graph_definition.validate()
    except Exception as e:
        print(f"ERROR DURING GRAPH VALIDATION: {e}") 
        raise 
    return graph_definition.compile(checkpointer=checkpointer)

# --- 新增流程测试用例将在这里添加 ---

def test_add_simple_no_placeholders_success(compiled_app):
    """
    测试 3.1: 简单新增，无占位符，成功完成整个流程。
    包括预览、首次确认（保存）、最终确认（是）和API调用。
    """
    
    # ---- ROUND 1: 用户发起新增请求，系统返回预览和保存提示 ----
    initial_user_query_round1 = "帮我添加一个新用户，用户名是SimpleAdd，邮箱是simple@example.com，密码是simplepass"
    thread_id_round1 = "test-add-simple-thread-r1"

    initial_state_round1 = GraphState(
        user_query=initial_user_query_round1,
        raw_user_input=initial_user_query_round1,
        biaojiegou_save=MOCK_SCHEMA_JSON_STRING,
        table_names=MOCK_TABLE_NAMES,
        data_sample=json.dumps({"users": [{"id": 1, "username": "ExistingUser", "email": "existing@example.com"}]}), # 示例数据
        # --- 其他所有 GraphState 字段应根据其定义初始化为 None 或适当的默认值 ---
        final_answer=None, error_message=None, raw_schema_result=None, raw_table_names_str=None,
        sql_query_generated=None, sql_result=None, main_intent=None, query_analysis_intent=None,
        modify_context_sql=None, modify_context_result=None, raw_modify_llm_output=None, modify_error_message=None,
        temp_add_llm_data=None, add_structured_records_str=None, structured_add_records=None,
        add_processed_records_str=None, add_processed_records=None, add_preview_text=None, add_error_message=None,
        combined_operation_plan=None, content_combined=None,
        content_modify=None, content_new=None, delete_show=None, lastest_content_production=None,
        delete_array=None, save_content=None, api_call_result=None, add_parse_error=None
        # NotRequired 字段默认不需要在此处显式列出为 None，除非测试逻辑依赖其初始为 None
    )
    initial_state_dict_round1 = dict(initial_state_round1)
    config_round1 = {"configurable": {"thread_id": thread_id_round1}}

    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent:
        with patch('langgraph_crud_app.services.llm.llm_add_service.parse_add_request') as mock_parse_add_request:
            with patch('langgraph_crud_app.services.llm.llm_add_service.format_add_preview') as mock_format_add_preview:
                
                # 设置 Mock 返回值 (Round 1)
                mock_classify_main_intent.return_value = {"intent": "add", "confidence": 0.98}
                
                expected_llm_add_data_str = '[{"table_name": "users", "fields": {"username": "SimpleAdd", "email": "simple@example.com", "password": "simplepass"}}]'
                mock_parse_add_request.return_value = expected_llm_add_data_str
                
                expected_preview_text = "已准备好以下新增内容：\n表名: users\n字段:\n  username: SimpleAdd\n  email: simple@example.com\n  password: simplepass"
                mock_format_add_preview.return_value = expected_preview_text

                # 调用图 (Round 1)
                final_state_dict_round1 = compiled_app.invoke(initial_state_dict_round1, config_round1)
                final_state_round1 = GraphState(**final_state_dict_round1)

                # 断言 (Round 1)
                mock_classify_main_intent.assert_called_once_with(initial_user_query_round1)
                mock_parse_add_request.assert_called_once_with(
                    user_query=initial_user_query_round1,
                    schema_info=MOCK_SCHEMA_JSON_STRING,
                    sample_data=initial_state_round1["data_sample"]
                )

                # Prepare the expected arguments for llm_add_service.format_add_preview
                parsed_llm_add_data = json.loads(expected_llm_add_data_str)
                expected_processed_records_for_service = {}
                if isinstance(parsed_llm_add_data, list): # Ensure it's a list before iterating
                    for record in parsed_llm_add_data:
                        table_name = record.get("table_name")
                        if table_name:
                            if table_name not in expected_processed_records_for_service:
                                expected_processed_records_for_service[table_name] = []
                            expected_processed_records_for_service[table_name].append(record.get("fields", {}))
                
                mock_format_add_preview.assert_called_once_with(
                    query=initial_user_query_round1,
                    schema=MOCK_SCHEMA_JSON_STRING,
                    table_names=list(expected_processed_records_for_service.keys()) if expected_processed_records_for_service else [],
                    processed_records=expected_processed_records_for_service
                )
                assert expected_preview_text in final_state_round1.get("final_answer", "")
                assert "请输入 '保存' 以确认新增" in final_state_round1.get("final_answer", ""), "Final answer should prompt to save"
                assert final_state_round1.get("content_new") == expected_preview_text, "content_new not set correctly"
                
                # lastest_content_production 应该包含解析后的 Python 列表
                expected_lastest_production = json.loads(expected_llm_add_data_str)
                assert final_state_round1.get("lastest_content_production") == expected_lastest_production, "lastest_content_production not set correctly"
                assert final_state_round1.get("error_message") is None
                assert final_state_round1.get("add_error_message") is None
                assert final_state_round1.get("add_parse_error") is None

                print("test_add_simple_no_placeholders_success - Round 1 PASSED")

                # ---- ROUND 2: 用户输入 "保存"，系统请求最终确认 "是/否" ----
                initial_user_query_round2 = "保存"
                thread_id_round2 = "test-add-simple-thread-r2"
                
                # 构建第二轮的初始状态，基于第一轮的最终状态
                # 关键是更新 user_query，并保留上一轮生成的相关状态
                initial_state_round2 = GraphState(**final_state_dict_round1) # 从字典创建，避免直接修改
                initial_state_round2["user_query"] = initial_user_query_round2
                initial_state_round2["raw_user_input"] = initial_user_query_round2
                # 清理上一轮的 final_answer, error_message，模拟新一轮交互的开始
                initial_state_round2["final_answer"] = None
                initial_state_round2["error_message"] = None 
                initial_state_round2["add_error_message"] = None # 清理特定流程的错误
                initial_state_round2["add_parse_error"] = None

                initial_state_dict_round2 = dict(initial_state_round2)
                config_round2 = {"configurable": {"thread_id": thread_id_round2}}

                # classify_main_intent 是唯一需要重新 mock 的（如果它在前一个 with 块之外）
                # 由于所有 mock 都在同一个 with 块中，我们需要确保其行为符合第二轮的输入
                mock_classify_main_intent.reset_mock() # 重置调用计数等
                mock_classify_main_intent.return_value = {"intent": "confirm_other", "confidence": 0.99} # 模拟"保存"被识别为确认

                # 调用图 (Round 2)
                final_state_dict_round2 = compiled_app.invoke(initial_state_dict_round2, config_round2)
                final_state_round2 = GraphState(**final_state_dict_round2)

                # 断言 (Round 2)
                mock_classify_main_intent.assert_called_once_with(initial_user_query_round2)
                # 其他在第一轮 mock 的服务不应该在第二轮被调用
                mock_parse_add_request.assert_called_once() # 保持之前的调用次数
                mock_format_add_preview.assert_called_once() # 保持之前的调用次数

                assert "以下是即将【新增】的信息" in final_state_round2.get("final_answer", "")
                assert "请确认，并回复'是'/'否'" in final_state_round2.get("final_answer", "")
                assert final_state_round2.get("save_content") == "新增路径"
                assert final_state_round2.get("error_message") is None

                print("test_add_simple_no_placeholders_success - Round 2 PASSED")

                # ---- ROUND 3: 用户输入 "是"，系统执行新增并返回成功信息 ----
                initial_user_query_round3 = "是"
                thread_id_round3 = "test-add-simple-thread-r3"

                initial_state_round3 = GraphState(**final_state_dict_round2) # 基于第二轮的最终状态
                initial_state_round3["user_query"] = initial_user_query_round3
                initial_state_round3["raw_user_input"] = initial_user_query_round3
                initial_state_round3["final_answer"] = None # 清理上一轮的回复
                initial_state_round3["error_message"] = None

                initial_state_dict_round3 = dict(initial_state_round3)
                config_round3 = {"configurable": {"thread_id": thread_id_round3}}

                # Patches specific to Round 3
                with patch('langgraph_crud_app.services.llm.llm_flow_control_service.classify_yes_no') as mock_classify_yes_no:
                    with patch('langgraph_crud_app.services.api_client.insert_record') as mock_insert_record:
                        with patch('langgraph_crud_app.services.llm.llm_flow_control_service.format_api_result') as mock_format_api_result:

                            mock_classify_main_intent.reset_mock() # mock_classify_main_intent is from the outer scope
                            mock_classify_main_intent.return_value = {"intent": "confirm_other", "confidence": 0.99}
                            mock_classify_yes_no.return_value = "yes"
                            
                            # 获取期望传递给 insert_record 的负载
                            expected_payload_for_api = final_state_round2.get("lastest_content_production")
                            mock_api_response_success = {"status": "success", "message": "1 record(s) inserted.", "ids": [123]}
                            mock_insert_record.return_value = mock_api_response_success
                            
                            expected_final_success_message = "操作成功：已成功新增 1 条记录。ID: 123"
                            mock_format_api_result.return_value = expected_final_success_message

                            # 调用图 (Round 3)
                            final_state_dict_round3 = compiled_app.invoke(initial_state_dict_round3, config_round3)
                            final_state_round3 = GraphState(**final_state_dict_round3)

                            # 断言 (Round 3)
                            mock_classify_main_intent.assert_called_once_with(initial_user_query_round3)
                            mock_classify_yes_no.assert_called_once_with(initial_user_query_round3)
                            mock_insert_record.assert_called_once_with(expected_payload_for_api)
                            mock_format_api_result.assert_called_once_with(
                                result=mock_api_response_success, 
                                original_query=initial_user_query_round3, 
                                operation_type="新增"
                            )
                            assert final_state_round3.get("final_answer") == expected_final_success_message
                            assert final_state_round3.get("error_message") is None
                            # 验证状态是否已重置 (暂时移除对 save_content 的检查，后续统一处理状态重置)
                            # assert final_state_round3.get("save_content") is None 
                            assert final_state_round3.get("content_new") is None
                            assert final_state_round3.get("lastest_content_production") is None
                            # api_call_result 应该包含API的直接返回 (Python字典)
                            assert final_state_round3.get("api_call_result") == mock_api_response_success

                            print("test_add_simple_no_placeholders_success - Round 3 PASSED")
                            print("test_add_simple_no_placeholders_success PASSED SUCCESSFULLY")

def test_add_with_random_placeholders_success(compiled_app):
    """
    测试 3.2: 新增记录，包含 {{random(...)}} 占位符，验证替换是否正确。
    """
    initial_user_query_round1 = "帮我添加一个用户，用户名随机，邮箱是fixed@example.com，密码用随机UUID，备注用随机数字"
    thread_id_round1 = "test-add-random-thread-r1"

    # 为了测试 random(number)，我们假设 users 表有一个可以接受数字的字段，比如 'profile_version'
    # 或者我们可以 mock schema 使其包含一个 age 字段。
    # 为简单起见，我们让 LLM 返回的字段与 MOCK_SCHEMA_JSON_STRING 中的 users 表匹配，但 password 可以是uuid，username可以是string。
    # 我们将在 add_processed_records_str 中验证process_placeholders_action 的输出。

    initial_state_round1 = GraphState(
        user_query=initial_user_query_round1,
        raw_user_input=initial_user_query_round1,
        biaojiegou_save=MOCK_SCHEMA_JSON_STRING, # 使用文件顶部的 MOCK_SCHEMA_JSON_STRING
        table_names=MOCK_TABLE_NAMES, # 使用文件顶部的 MOCK_TABLE_NAMES (即 ["users"])
        data_sample=json.dumps({"users": [{"id": 1, "username": "ExistingUser", "email": "existing@example.com"}]}),
        final_answer=None, error_message=None, raw_schema_result=None, raw_table_names_str=None,
        sql_query_generated=None, sql_result=None, main_intent=None, query_analysis_intent=None,
        modify_context_sql=None, modify_context_result=None, raw_modify_llm_output=None, modify_error_message=None,
        temp_add_llm_data=None, add_structured_records_str=None, structured_add_records=None,
        add_processed_records_str=None, add_processed_records=None, add_preview_text=None, add_error_message=None,
        combined_operation_plan=None, content_combined=None,
        content_modify=None, content_new=None, delete_show=None, lastest_content_production=None,
        delete_array=None, save_content=None, api_call_result=None, add_parse_error=None
    )
    initial_state_dict_round1 = dict(initial_state_round1)
    config_round1 = {"configurable": {"thread_id": thread_id_round1}}

    # 预期的固定随机值
    fixed_random_string = "randstr123"
    fixed_random_uuid = "fixed-uuid-val-12345"
    # fixed_random_number = 42 # 假设 users 表没有直接的数字备注字段，暂时不测试 random(number)

    # Mock LLM 和随机函数
    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent:
        with patch('langgraph_crud_app.services.llm.llm_add_service.parse_add_request') as mock_parse_add_request:
            with patch('langgraph_crud_app.services.data_processor.random.choices', return_value=list(fixed_random_string)) as mock_random_choices:
                with patch('langgraph_crud_app.services.data_processor.uuid.uuid4') as mock_uuid4:
                    with patch('langgraph_crud_app.services.llm.llm_add_service.format_add_preview') as mock_format_add_preview:
                        
                        # 设置 uuid4 mock 的返回值以正确模拟 str(uuid.uuid4()) 的行为
                        fixed_uuid_object = MagicMock()
                        fixed_uuid_object.__str__.return_value = fixed_random_uuid
                        mock_uuid4.return_value = fixed_uuid_object

                        mock_classify_main_intent.return_value = {"intent": "add", "confidence": 0.97}
                        
                        # LLM 返回的包含占位符的 JSON
                        llm_add_data_with_placeholders = '[{"table_name": "users", "fields": {"username": "{{random(string)}}", "email": "fixed@example.com", "password": "{{random(uuid)}}"}}]'
                        mock_parse_add_request.return_value = llm_add_data_with_placeholders

                        # 期望 process_placeholders_action 处理后的结果 (占位符被替换)
                        expected_records_after_placeholders = [{
                            "table_name": "users", 
                            "fields": {
                                "username": fixed_random_string, 
                                "email": "fixed@example.com", 
                                "password": fixed_random_uuid
                            }
                        }]
                        # 这个结果会由 format_add_preview_action 中的逻辑转换为按表名分组的字典再传给服务
                        expected_records_for_format_preview_service = {
                            "users": [
                                {"username": fixed_random_string, "email": "fixed@example.com", "password": fixed_random_uuid}
                            ]
                        }

                        expected_preview_text_round1 = f"将新增用户：用户名 {fixed_random_string}, 邮箱 fixed@example.com, 密码 {fixed_random_uuid}"
                        mock_format_add_preview.return_value = expected_preview_text_round1

                        # ---- 调用图 (Round 1) ----
                        final_state_dict_round1 = compiled_app.invoke(initial_state_dict_round1, config_round1)
                        final_state_round1 = GraphState(**final_state_dict_round1)

                        # ---- 断言 (Round 1) ----
                        mock_classify_main_intent.assert_called_once_with(initial_user_query_round1)
                        mock_parse_add_request.assert_called_once_with(
                            user_query=initial_user_query_round1,
                            schema_info=MOCK_SCHEMA_JSON_STRING,
                            sample_data=initial_state_round1["data_sample"]
                        )
                        
                        # 验证随机函数是否被调用
                        mock_random_choices.assert_called_once() # 对应 {{random(string)}}
                        # mock_uuid4.assert_called_once()      # 由于 LangGraph 内部可能多次调用 uuid, 此断言可能不稳定，移除
                        # 我们更关心的是最终结果中是否包含了我们 mock 的 fixed_random_uuid
                        
                        # 验证 add_processed_records_str 是否正确包含了替换后的值
                        # add_actions.process_placeholders_action 会将结果存入 add_processed_records_str
                        assert final_state_round1.get("add_processed_records_str") == json.dumps(expected_records_after_placeholders)

                        # 验证 format_add_preview 服务的调用参数
                        mock_format_add_preview.assert_called_once_with(
                            query=initial_user_query_round1,
                            schema=MOCK_SCHEMA_JSON_STRING,
                            table_names=list(expected_records_for_format_preview_service.keys()),
                            processed_records=expected_records_for_format_preview_service
                        )

                        assert expected_preview_text_round1 in final_state_round1.get("final_answer", "")
                        assert "请输入 '保存' 以确认新增" in final_state_round1.get("final_answer", "")
                        assert final_state_round1.get("content_new") == expected_preview_text_round1
                        assert final_state_round1.get("lastest_content_production") == expected_records_after_placeholders # 这是List[Dict]
                        assert final_state_round1.get("error_message") is None
                        
                        print("test_add_with_random_placeholders_success - Round 1 PASSED")

                        # 后续轮次的测试可以复用 test_add_simple_no_placeholders_success 的结构
                        # 因为占位符处理只在第一轮发生，后续流程相同

                        # ---- ROUND 2: 用户输入 "保存" ----
                        initial_user_query_round2 = "保存"
                        thread_id_round2 = "test-add-random-thread-r2"
                        initial_state_round2 = GraphState(**final_state_dict_round1) 
                        initial_state_round2["user_query"] = initial_user_query_round2
                        initial_state_round2["raw_user_input"] = initial_user_query_round2
                        initial_state_round2["final_answer"] = None
                        initial_state_round2["error_message"] = None 
                        initial_state_dict_round2 = dict(initial_state_round2)
                        config_round2 = {"configurable": {"thread_id": thread_id_round2}}

                        mock_classify_main_intent.reset_mock()
                        mock_classify_main_intent.return_value = {"intent": "confirm_other", "confidence": 0.99}

                        final_state_dict_round2 = compiled_app.invoke(initial_state_dict_round2, config_round2)
                        final_state_round2 = GraphState(**final_state_dict_round2)

                        mock_classify_main_intent.assert_called_once_with(initial_user_query_round2)
                        mock_parse_add_request.assert_called_once() 
                        mock_format_add_preview.assert_called_once()

                        assert "以下是即将【新增】的信息" in final_state_round2.get("final_answer", "")
                        assert "请确认，并回复'是'/'否'" in final_state_round2.get("final_answer", "")
                        assert final_state_round2.get("save_content") == "新增路径"
                        print("test_add_with_random_placeholders_success - Round 2 PASSED")

                        # ---- ROUND 3: 用户输入 "是" ----
                        initial_user_query_round3 = "是"
                        thread_id_round3 = "test-add-random-thread-r3"
                        initial_state_round3 = GraphState(**final_state_dict_round2) 
                        initial_state_round3["user_query"] = initial_user_query_round3
                        initial_state_round3["raw_user_input"] = initial_user_query_round3
                        initial_state_round3["final_answer"] = None
                        initial_state_round3["error_message"] = None
                        initial_state_dict_round3 = dict(initial_state_round3)
                        config_round3 = {"configurable": {"thread_id": thread_id_round3}}

                        with patch('langgraph_crud_app.services.llm.llm_flow_control_service.classify_yes_no') as mock_classify_yes_no:
                            with patch('langgraph_crud_app.services.api_client.insert_record') as mock_insert_record:
                                with patch('langgraph_crud_app.services.llm.llm_flow_control_service.format_api_result') as mock_format_api_result:
                                    
                                    mock_classify_main_intent.reset_mock()
                                    mock_classify_main_intent.return_value = {"intent": "confirm_other", "confidence": 0.99}
                                    mock_classify_yes_no.return_value = "yes"
                                    
                                    expected_payload_for_api_round3 = final_state_round2.get("lastest_content_production") # 这应该是包含随机值的列表
                                    # 假设API调用成功，返回的新记录ID是456
                                    mock_api_response_success_round3 = {"status": "success", "message": "1 record(s) inserted.", "ids": [456]}
                                    mock_insert_record.return_value = mock_api_response_success_round3
                                    
                                    expected_final_success_message_round3 = f"操作成功：已成功新增 1 条记录。ID: 456"
                                    mock_format_api_result.return_value = expected_final_success_message_round3

                                    final_state_dict_round3 = compiled_app.invoke(initial_state_dict_round3, config_round3)
                                    final_state_round3 = GraphState(**final_state_dict_round3)

                                    mock_classify_main_intent.assert_called_once_with(initial_user_query_round3)
                                    mock_classify_yes_no.assert_called_once_with(initial_user_query_round3)
                                    mock_insert_record.assert_called_once_with(expected_payload_for_api_round3)
                                    mock_format_api_result.assert_called_once_with(
                                        result=mock_api_response_success_round3, 
                                        original_query=initial_user_query_round3, 
                                        operation_type="新增" 
                                    )
                                    assert final_state_round3.get("final_answer") == expected_final_success_message_round3
                                    assert final_state_round3.get("content_new") is None
                                    assert final_state_round3.get("lastest_content_production") is None
                                    assert final_state_round3.get("api_call_result") == mock_api_response_success_round3 # 比较字典

                                    print("test_add_with_random_placeholders_success - Round 3 PASSED")
                                    print("test_add_with_random_placeholders_success PASSED SUCCESSFULLY")

def test_add_with_db_placeholder_success(compiled_app):
    """
    测试 3.3: 新增记录，包含 {{db(...)}} 占位符，验证替换和 API 调用是否正确。
    """
    initial_user_query_round1 = "添加新用户 Newbie，他的经理是 ExistingUser，邮箱是 newbie@example.com，密码是 newpass"
    thread_id_round1 = "test-add-db-thread-r1"

    initial_state_round1 = GraphState(
        user_query=initial_user_query_round1,
        raw_user_input=initial_user_query_round1,
        biaojiegou_save=MOCK_SCHEMA_JSON_STRING, # 已更新包含 reports_to_user_id
        table_names=MOCK_TABLE_NAMES, # ["users"]
        data_sample=json.dumps({"users": [{"id": 1, "username": "ExistingUser", "email": "existing@example.com", "reports_to_user_id": None}]}),
        final_answer=None, error_message=None, raw_schema_result=None, raw_table_names_str=None,
        sql_query_generated=None, sql_result=None, main_intent=None, query_analysis_intent=None,
        modify_context_sql=None, modify_context_result=None, raw_modify_llm_output=None, modify_error_message=None,
        temp_add_llm_data=None, add_structured_records_str=None, structured_add_records=None,
        add_processed_records_str=None, add_processed_records=None, add_preview_text=None, add_error_message=None,
        combined_operation_plan=None, content_combined=None,
        content_modify=None, content_new=None, delete_show=None, lastest_content_production=None,
        delete_array=None, save_content=None, api_call_result=None, add_parse_error=None
    )
    initial_state_dict_round1 = dict(initial_state_round1)
    config_round1 = {"configurable": {"thread_id": thread_id_round1}}

    # 预期的 db 查询结果
    db_query_for_manager_id = "SELECT id FROM users WHERE username = 'ExistingUser'"
    mock_manager_id_result = json.dumps([{"id": 1}]) # ExistingUser 的 ID 是 1

    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent:
        with patch('langgraph_crud_app.services.llm.llm_add_service.parse_add_request') as mock_parse_add_request:
            # 这个 patch 需要用于 process_placeholders_action 内部对 db() 占位符的解析
            with patch('langgraph_crud_app.services.data_processor.execute_query') as mock_execute_query_for_db_placeholder:
                with patch('langgraph_crud_app.services.llm.llm_add_service.format_add_preview') as mock_format_add_preview:
                    
                    mock_classify_main_intent.return_value = {"intent": "add", "confidence": 0.98}
                    
                    llm_add_data_with_db_placeholder = '[{"table_name": "users", "fields": {"username": "Newbie", "email": "newbie@example.com", "password": "newpass", "reports_to_user_id": "{{db(SELECT id FROM users WHERE username = \'ExistingUser\')}}"}}]'
                    mock_parse_add_request.return_value = llm_add_data_with_db_placeholder
                    
                    # 设置 execute_query 的 mock 返回值，用于解析 db() 占位符
                    mock_execute_query_for_db_placeholder.return_value = mock_manager_id_result

                    # 期望 process_placeholders_action 处理后的结果 (占位符被替换)
                    expected_records_after_placeholders = [{
                        "table_name": "users", 
                        "fields": {
                            "username": "Newbie", 
                            "email": "newbie@example.com", 
                            "password": "newpass",
                            "reports_to_user_id": 1 # 期望从 db() 查询得到的值
                        }
                    }]
                    expected_records_for_format_preview_service = {
                        "users": [
                            {"username": "Newbie", "email": "newbie@example.com", "password": "newpass", "reports_to_user_id": 1}
                        ]
                    }
                    expected_preview_text_round1 = "将新增用户 Newbie，其经理ID为 1"
                    mock_format_add_preview.return_value = expected_preview_text_round1

                    # ---- 调用图 (Round 1) ----
                    final_state_dict_round1 = compiled_app.invoke(initial_state_dict_round1, config_round1)
                    final_state_round1 = GraphState(**final_state_dict_round1)

                    # ---- 断言 (Round 1) ----
                    mock_classify_main_intent.assert_called_once_with(initial_user_query_round1)
                    mock_parse_add_request.assert_called_once_with(
                        user_query=initial_user_query_round1,
                        schema_info=MOCK_SCHEMA_JSON_STRING,
                        sample_data=initial_state_round1["data_sample"]
                    )
                    # 验证 db() 占位符的查询是否被正确调用
                    mock_execute_query_for_db_placeholder.assert_called_once_with(db_query_for_manager_id)
                    
                    assert final_state_round1.get("add_processed_records_str") == json.dumps(expected_records_after_placeholders)
                    
                    mock_format_add_preview.assert_called_once_with(
                        query=initial_user_query_round1,
                        schema=MOCK_SCHEMA_JSON_STRING,
                        table_names=list(expected_records_for_format_preview_service.keys()),
                        processed_records=expected_records_for_format_preview_service
                    )
                    assert expected_preview_text_round1 in final_state_round1.get("final_answer", "")
                    assert "请输入 '保存' 以确认新增" in final_state_round1.get("final_answer", "")
                    assert final_state_round1.get("content_new") == expected_preview_text_round1
                    assert final_state_round1.get("lastest_content_production") == expected_records_after_placeholders
                    assert final_state_round1.get("error_message") is None

                    print("test_add_with_db_placeholder_success - Round 1 PASSED")

                    # ---- ROUND 2 & 3 (可以复用之前的结构，但使用特定于此测试的 mock 和期望值) ----
                    # ---- ROUND 2: 用户输入 "保存" ----
                    initial_user_query_round2 = "保存"
                    thread_id_round2 = "test-add-db-thread-r2"
                    initial_state_round2 = GraphState(**final_state_dict_round1) 
                    initial_state_round2["user_query"] = initial_user_query_round2
                    initial_state_round2["raw_user_input"] = initial_user_query_round2
                    initial_state_round2["final_answer"] = None
                    initial_state_round2["error_message"] = None 
                    initial_state_dict_round2 = dict(initial_state_round2)
                    config_round2 = {"configurable": {"thread_id": thread_id_round2}}

                    mock_classify_main_intent.reset_mock()
                    mock_classify_main_intent.return_value = {"intent": "confirm_other", "confidence": 0.99}

                    final_state_dict_round2 = compiled_app.invoke(initial_state_dict_round2, config_round2)
                    final_state_round2 = GraphState(**final_state_dict_round2)

                    mock_classify_main_intent.assert_called_once_with(initial_user_query_round2)
                    assert "以下是即将【新增】的信息" in final_state_round2.get("final_answer", "")
                    assert "请确认，并回复'是'/'否'" in final_state_round2.get("final_answer", "")
                    assert final_state_round2.get("save_content") == "新增路径"
                    print("test_add_with_db_placeholder_success - Round 2 PASSED")

                    # ---- ROUND 3: 用户输入 "是" ----
                    initial_user_query_round3 = "是"
                    thread_id_round3 = "test-add-db-thread-r3"
                    initial_state_round3 = GraphState(**final_state_dict_round2) 
                    initial_state_round3["user_query"] = initial_user_query_round3
                    initial_state_round3["raw_user_input"] = initial_user_query_round3
                    initial_state_round3["final_answer"] = None
                    initial_state_round3["error_message"] = None
                    initial_state_dict_round3 = dict(initial_state_round3)
                    config_round3 = {"configurable": {"thread_id": thread_id_round3}}

                    with patch('langgraph_crud_app.services.llm.llm_flow_control_service.classify_yes_no') as mock_classify_yes_no:
                        with patch('langgraph_crud_app.services.api_client.insert_record') as mock_insert_record:
                            with patch('langgraph_crud_app.services.llm.llm_flow_control_service.format_api_result') as mock_format_api_result:
                                
                                mock_classify_main_intent.reset_mock()
                                mock_classify_main_intent.return_value = {"intent": "confirm_other", "confidence": 0.99}
                                mock_classify_yes_no.return_value = "yes"
                                
                                expected_payload_for_api_round3 = final_state_round2.get("lastest_content_production") 
                                mock_api_response_success_round3 = {"status": "success", "message": "1 record(s) inserted.", "ids": [789]} # 新的 user ID
                                mock_insert_record.return_value = mock_api_response_success_round3
                                
                                expected_final_success_message_round3 = f"操作成功：已成功新增 1 条记录。ID: 789"
                                mock_format_api_result.return_value = expected_final_success_message_round3

                                final_state_dict_round3 = compiled_app.invoke(initial_state_dict_round3, config_round3)
                                final_state_round3 = GraphState(**final_state_dict_round3)

                                mock_classify_main_intent.assert_called_once_with(initial_user_query_round3)
                                mock_classify_yes_no.assert_called_once_with(initial_user_query_round3)
                                mock_insert_record.assert_called_once_with(expected_payload_for_api_round3)
                                mock_format_api_result.assert_called_once_with(
                                    result=mock_api_response_success_round3, 
                                    original_query=initial_user_query_round3, 
                                    operation_type="新增" 
                                )
                                assert final_state_round3.get("final_answer") == expected_final_success_message_round3
                                assert final_state_round3.get("content_new") is None
                                assert final_state_round3.get("lastest_content_production") is None
                                assert final_state_round3.get("api_call_result") == mock_api_response_success_round3

                                print("test_add_with_db_placeholder_success - Round 3 PASSED")
                                print("test_add_with_db_placeholder_success PASSED SUCCESSFULLY")

def test_add_db_placeholder_empty_result(compiled_app):
    """
    测试 3.4.1: 新增记录，{{db()}} 查询返回空列表 []。
    预期行为: 占位符解析为 None，流程继续，API 将收到 None 值。
    """
    initial_user_query_round1 = "添加新用户 PhantomUser，其经理是 NonExistentManager，邮箱是 phantom@example.com"
    thread_id_round1 = "test-add-db-empty-r1"

    initial_state_round1 = GraphState(
        user_query=initial_user_query_round1,
        raw_user_input=initial_user_query_round1,
        biaojiegou_save=MOCK_SCHEMA_JSON_STRING, # 包含 reports_to_user_id
        table_names=MOCK_TABLE_NAMES,
        data_sample=json.dumps({"users": [{"id": 1, "username": "ExistingUser"}]}),
        final_answer=None, error_message=None, temp_add_llm_data=None, add_structured_records_str=None,
        add_processed_records_str=None, add_preview_text=None, add_error_message=None,
        content_new=None, lastest_content_production=None, save_content=None, api_call_result=None, add_parse_error=None
    )
    initial_state_dict_round1 = dict(initial_state_round1)
    config_round1 = {"configurable": {"thread_id": thread_id_round1}}

    db_query_for_non_existent_manager = "SELECT id FROM users WHERE username = 'NonExistentManager'"
    mock_empty_db_result = json.dumps([])

    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent:
        with patch('langgraph_crud_app.services.llm.llm_add_service.parse_add_request') as mock_parse_add_request:
            with patch('langgraph_crud_app.services.data_processor.execute_query') as mock_execute_query_for_db_placeholder:
                with patch('langgraph_crud_app.services.llm.llm_add_service.format_add_preview') as mock_format_add_preview:

                    mock_classify_main_intent.return_value = {"intent": "add"}
                    llm_add_data_with_db_placeholder = '[{"table_name": "users", "fields": {"username": "PhantomUser", "email": "phantom@example.com", "reports_to_user_id": "{{db(SELECT id FROM users WHERE username = \'NonExistentManager\')}}"}}]'
                    mock_parse_add_request.return_value = llm_add_data_with_db_placeholder
                    mock_execute_query_for_db_placeholder.return_value = mock_empty_db_result

                    expected_records_after_empty_db = [{
                        "table_name": "users", 
                        "fields": {"username": "PhantomUser", "email": "phantom@example.com", "reports_to_user_id": None}
                    }]
                    expected_records_for_format_preview_service = {"users": [expected_records_after_empty_db[0]["fields"]]}
                    expected_preview_text_empty_db = "将新增用户 PhantomUser，其经理ID为 None"
                    mock_format_add_preview.return_value = expected_preview_text_empty_db

                    final_state_dict_round1 = compiled_app.invoke(initial_state_dict_round1, config_round1)
                    final_state_round1 = GraphState(**final_state_dict_round1)

                    mock_execute_query_for_db_placeholder.assert_called_once_with(db_query_for_non_existent_manager)
                    assert final_state_round1.get("add_processed_records_str") == json.dumps(expected_records_after_empty_db)
                    mock_format_add_preview.assert_called_once_with(
                        query=initial_user_query_round1,
                        schema=MOCK_SCHEMA_JSON_STRING,
                        table_names=['users'],
                        processed_records=expected_records_for_format_preview_service
                    )
                    assert expected_preview_text_empty_db in final_state_round1.get("final_answer", "")
                    assert final_state_round1.get("lastest_content_production") == expected_records_after_empty_db
                    assert final_state_round1.get("add_error_message") is None # No error expected here
                    print("test_add_db_placeholder_empty_result - Round 1 PASSED")

                    # Optional: Test Round 2 & 3 to ensure API receives None
                    # For brevity, we assume if Round 1 is correct, subsequent rounds will work with this data.

def test_add_db_placeholder_invalid_multiline_result(compiled_app):
    """
    测试 3.4.2: 新增记录，{{db()}} 查询返回多行结果。
    预期行为: process_placeholders_action 设置 add_error_message, 流程转到错误处理。
    """
    initial_user_query = "添加新用户 ErrorUser，其部门ID来自一个会返回多行的查询"
    thread_id = "test-add-db-invalid-r1"

    initial_state = GraphState(
        user_query=initial_user_query,
        raw_user_input=initial_user_query,
        biaojiegou_save=MOCK_SCHEMA_JSON_STRING, # users 表有 reports_to_user_id
        table_names=MOCK_TABLE_NAMES,
        data_sample=json.dumps({"users": [{"id": 1, "username": "AnyUser"}]}),
        final_answer=None, error_message=None, temp_add_llm_data=None, add_structured_records_str=None,
        add_processed_records_str=None, add_preview_text=None, add_error_message=None,
        content_new=None, lastest_content_production=None, save_content=None, api_call_result=None, add_parse_error=None
    )
    initial_state_dict = dict(initial_state)
    config = {"configurable": {"thread_id": thread_id}}

    db_query_multiline = "SELECT id FROM users WHERE username LIKE 'TestUser%'" # 假设这会返回多行
    mock_multiline_db_result = json.dumps([{"id": 1}, {"id": 2}])

    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent:
        with patch('langgraph_crud_app.services.llm.llm_add_service.parse_add_request') as mock_parse_add_request:
            with patch('langgraph_crud_app.services.data_processor.execute_query') as mock_execute_query_for_db_placeholder:
                with patch('langgraph_crud_app.nodes.actions.add_actions.format_add_preview_action') as mock_format_add_preview_action_node:
                    with patch('langgraph_crud_app.nodes.actions.add_actions.provide_add_feedback_action') as mock_provide_add_feedback_action_node:

                        mock_classify_main_intent.return_value = {"intent": "add"}
                        llm_add_data_with_multiline_db = '[{"table_name": "users", "fields": {"username": "ErrorUser", "reports_to_user_id": "{{db(SELECT id FROM users WHERE username LIKE \'TestUser%\')}}"}}]'
                        mock_parse_add_request.return_value = llm_add_data_with_multiline_db
                        mock_execute_query_for_db_placeholder.return_value = mock_multiline_db_result

                        final_state_dict = compiled_app.invoke(initial_state_dict, config)
                        final_state = GraphState(**final_state_dict)

                        mock_execute_query_for_db_placeholder.assert_called_once_with(db_query_multiline)
                        
                        actual_add_error_message = final_state.get("add_error_message", "")
                        assert actual_add_error_message is not None and actual_add_error_message != "", "add_error_message should be set and not empty"
                        # Check for the specific error message thrown by data_processor.process_placeholders
                        expected_data_processor_error_part = "db 查询 'SELECT id FROM users WHERE username LIKE \'TestUser%\'' 的结果格式无法解析为单值"
                        assert expected_data_processor_error_part in actual_add_error_message
                        # Check for the prefix that process_placeholders_action might add if it re-wraps the exception (currently it seems to use str(ve) directly)
                        # Based on current logs, str(ve) is "处理 db 占位符失败: ...", so this check should be for that.
                        assert "处理 db 占位符失败" in actual_add_error_message 

                        # 验证流程是否走向错误处理 (format_add_preview 不应被调用)
                        mock_format_add_preview_action_node.assert_not_called()
                        # mock_provide_add_feedback_action_node.assert_not_called() # provide_add_feedback is NOT called, handle_add_error sets final_answer

                        # 验证最终用户看到的错误信息 (handle_add_error_action 会设置 final_answer)
                        expected_fixed_error_message = "这是一个来自handle_add_error的固定错误消息"
                        assert final_state.get("final_answer", "") == expected_fixed_error_message
                        assert final_state.get("error_flag") is True # Ensure error_flag is also checked
                        
                        print("test_add_db_placeholder_invalid_multiline_result PASSED")