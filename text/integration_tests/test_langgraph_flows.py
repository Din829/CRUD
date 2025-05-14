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
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.base import BaseCheckpointSaver, CheckpointTuple, RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

# 最小有效 schema，作为 JSON 字符串
MOCK_SCHEMA_JSON_STRING = json.dumps({
    "users": {
        "fields": {
            "id": {"type": "int", "key": "PRI", "null": "NO", "default": None},
            "name": {"type": "varchar(255)", "key": "", "null": "YES", "default": None},
            "email": {"type": "varchar(255)", "key": "UNI", "null": "YES", "default": None}
        },
        "constraints": [
            {"name": "PRIMARY", "type": "PRIMARY KEY", "columns": ["id"]},
            {"name": "email", "type": "UNIQUE KEY", "columns": ["email"]}
        ],
        "description": "用于存储用户信息的表。"
    },
    "prompts": {
        "fields": {
            "id": {"type": "int", "key": "PRI", "null": "NO", "default": None},
            "user_id": {"type": "int", "key": "MUL", "null": "YES", "default": None},
            "title": {"type": "varchar(255)", "key": "", "null": "YES", "default": None}
        },
        "constraints": [
            {"name": "PRIMARY", "type": "PRIMARY KEY", "columns": ["id"]},
            {"name": "user_id", "type": "FOREIGN KEY", "columns": ["user_id"], "references": "users(id)"}
        ],
        "description": "用于存储用户提示的表。"
    }
})

MOCK_TABLE_NAMES = ["users", "prompts"]

@pytest.fixture
def memory_saver_instance_mock():
    """创建一个模拟的 CheckpointSaver 实例，遵循 BaseCheckpointSaver 接口。"""
    mock_instance = MagicMock(spec=BaseCheckpointSaver)
    
    mock_instance.get_tuple.return_value = None
    mock_instance.get.return_value = None
    
    # 模拟 put 方法，返回传入的 config
    # 增加打印语句来检查 checkpoint 的内容
    def put_side_effect(config, checkpoint, metadata):
        print(f"[DEBUG] memory_saver_instance_mock.put called with:")
        print(f"  config: {config}")
        print(f"  checkpoint: {checkpoint}") # 重点关注 checkpoint['channel_versions']
        print(f"  metadata: {metadata}")
        # 确保返回的是干净的字典，避免 MagicMock 干扰 config 本身
        # 如果 config 本身也可能被污染，我们可能需要返回一个 config 的深拷贝或构造的新字典
        return config # 或者 return dict(config) or copy.deepcopy(config) if necessary
    
    mock_instance.put.side_effect = put_side_effect
    
    # 可选：为 put_tuple 添加模拟，以防 langgraph 直接调用
    # 根据 SqliteSaver，put_tuple 返回 List[RunnableConfig] 或 RunnableConfig
    # def put_tuple_side_effect(config, checkpoint_tuples):
    #     print(f"[DEBUG] memory_saver_instance_mock.put_tuple called with:")
    #     print(f"  config: {config}")
    #     print(f"  checkpoint_tuples: {checkpoint_tuples}")
    #     return [config] # 或者只返回 config，取决于 langgraph 的期望

    # mock_instance.put_tuple.side_effect = put_tuple_side_effect
    # 暂时移除 put_tuple 的 mock，因为 spec=BaseCheckpointSaver 时 AttributeError
    # 主要依赖 put 方法的 mock 和其中的打印
  
    return mock_instance

@pytest.fixture
def compiled_app():
    """提供带有内存 checkpointer 的已编译 LangGraph 应用。"""
    graph_definition = build_graph()
    checkpointer = InMemorySaver()
    app = graph_definition.compile(checkpointer=checkpointer)
    return app

def test_simple_select_query_success(compiled_app):
    """
    测试 2.1.1 - 2.1.6: 一个简单的 SELECT 查询成功通过图。
    - Mock classify_main_intent -> query_analysis
    - Mock classify_query_analysis_intent -> query
    - Mock generate_select_sql -> 有效的 SELECT SQL
    - Mock execute_sql_query -> 成功的结果
    - Mock format_query_result -> 格式化的文本
    - 验证 final_answer
    """
    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent, \
         patch('langgraph_crud_app.services.llm.llm_query_service.classify_query_analysis_intent') as mock_classify_query_analysis_intent, \
         patch('langgraph_crud_app.services.llm.llm_query_service.generate_select_sql') as mock_generate_select_sql, \
         patch('langgraph_crud_app.services.api_client.execute_query') as mock_execute_sql_query, \
         patch('langgraph_crud_app.services.llm.llm_query_service.format_query_result') as mock_format_query_result:

        # --- 设置 Mock 返回值 ---
        mock_classify_main_intent.return_value = {
            "intent": "query_analysis", "confidence": 0.95, "details": "用户想要查询或分析数据。",
            "matched_keywords": ["查找"], "main_intent_debug_log": "主意图分类的调试日志。"
        }
        mock_classify_query_analysis_intent.return_value = {
            "intent": "query", "confidence": 0.92, "details": "这是一个简单的 SELECT 查询。",
            "query_type": "SELECT_SINGLE_TABLE", "sub_intent_debug_log": "子意图的调试日志。"
        }
        # expected_sql 现在应该包含 clean_sql_action 添加的分号
        expected_sql_for_assertion = "SELECT id, name, email FROM users WHERE name = 'Alice';"
        expected_sql_from_llm = "SELECT id, name, email FROM users WHERE name = 'Alice'"
        mock_generate_select_sql.return_value = expected_sql_from_llm # LLM 返回不带分号的 SQL
        
        mock_db_results = [{"id": 1, "name": "Alice", "email": "alice@example.com"}]
        mock_execute_sql_query.return_value = mock_db_results
        
        expected_formatted_answer = "找到了1位用户：Alice (alice@example.com)。"
        mock_format_query_result.return_value = expected_formatted_answer

        # --- 准备初始图状态 ---
        initial_state = GraphState(
            user_query="查找用户名为Alice的记录",
            raw_user_input="查找用户名为Alice的记录",
            biaojiegou_save=MOCK_SCHEMA_JSON_STRING, table_names=MOCK_TABLE_NAMES,
            data_sample=json.dumps({"users": [{"id": 1, "name": "Bob"}]}),
            final_answer=None, error_message=None,
            query_intent=None, generated_sql_action=None, sql_query_result_action=None, clarification_needed_action=None,
            current_action_node=None, previous_action_node=None, save_content=None, content_add=None, content_modify=None,
            content_delete=None, content_combined=None, main_intent_classification_details=None, sub_intent_classification_details=None,
            sql_generation_details=None, sql_execution_details=None, query_formatting_details=None, operation_response_details=None,
            is_phi_present=False, sql_string_for_execution=None, last_executed_sql_node=None, last_successful_execution_data=None,
            llm_call_history_for_intent_classification=[], llm_call_history_for_data_operations=[], user_feedback_history=[]
        )
        initial_state_dict = dict(initial_state)

        # --- 调用图 ---
        config = {"configurable": {"thread_id": "test-query-thread-1"}}
        final_state_dict = compiled_app.invoke(initial_state_dict, config=config)
        final_state = GraphState(**final_state_dict)

        # --- 断言 ---
        assert final_state.get("final_answer") == expected_formatted_answer
        assert final_state.get("error_message") is None, f"期望没有错误，但得到: {final_state.get('error_message')}"

        mock_classify_main_intent.assert_called_once()
        mock_classify_query_analysis_intent.assert_called_once()
        mock_generate_select_sql.assert_called_once()
        # api_client.execute_query 函数接收到的参数是 clean_sql_action 清理后的 SQL (带分号)
        mock_execute_sql_query.assert_called_once_with(expected_sql_for_assertion)
        mock_format_query_result.assert_called_once()

        print("test_simple_select_query_success 已通过 (基本断言)。更详细的参数检查至关重要，需要根据节点逻辑来实现。")

def test_analysis_query_count_success(compiled_app):
    """
    测试 2.2: 一个分析查询 (如 COUNT(*)) 成功通过图。
    - Mock classify_main_intent -> query_analysis
    - Mock classify_query_analysis_intent -> analysis
    - Mock generate_analysis_sql -> 有效的 COUNT SQL
    - Mock execute_sql_query -> 成功的结果
    - Mock analyze_analysis_result -> 格式化的分析文本
    - 验证 final_answer
    """
    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent, \
         patch('langgraph_crud_app.services.llm.llm_query_service.classify_query_analysis_intent') as mock_classify_query_analysis_intent, \
         patch('langgraph_crud_app.services.llm.llm_query_service.generate_analysis_sql') as mock_generate_analysis_sql, \
         patch('langgraph_crud_app.services.api_client.execute_query') as mock_execute_sql_query, \
         patch('langgraph_crud_app.services.llm.llm_query_service.analyze_analysis_result') as mock_analyze_analysis_result:

        # --- 设置 Mock 返回值 ---
        mock_classify_main_intent.return_value = {
            "intent": "query_analysis", "confidence": 0.95, "details": "用户想要查询或分析数据。",
            "matched_keywords": ["统计"], "main_intent_debug_log": "主意图分类的调试日志。"
        }
        mock_classify_query_analysis_intent.return_value = "analysis"
        
        # generate_analysis_sql 返回不带分号的 SQL
        expected_sql_from_llm = "SELECT COUNT(*) FROM users"
        mock_generate_analysis_sql.return_value = expected_sql_from_llm
        
        # execute_query 接收到的是 clean_sql_action 清理后的 SQL (带分号)
        expected_sql_for_assertion = "SELECT COUNT(*) FROM users;"
        
        mock_db_results = [{"COUNT(*)": 5}] # 数据库返回的分析结果
        mock_execute_sql_query.return_value = mock_db_results
        
        expected_analytical_answer = "数据库中总共有 5 位用户。"
        # analyze_analysis_result 接收数据库结果和原始查询等作为输入
        mock_analyze_analysis_result.return_value = expected_analytical_answer

        # --- 准备初始图状态 ---
        initial_user_query = "统计一下我们有多少用户"
        initial_state = GraphState(
            user_query=initial_user_query,
            raw_user_input=initial_user_query,
            biaojiegou_save=MOCK_SCHEMA_JSON_STRING, table_names=MOCK_TABLE_NAMES,
            data_sample=json.dumps({"users": [{"id": 1, "name": "Bob"}, {"id": 2, "name": "Alice"}]}), # 示例数据可能与COUNT结果不完全对应，但此处不影响LLM mock
            final_answer=None, error_message=None,
            # 根据 GraphState 定义填充其他必要字段为 None 或默认值
            query_intent=None, generated_sql_action=None, sql_query_result_action=None, clarification_needed_action=None,
            current_action_node=None, previous_action_node=None, save_content=None, content_add=None, content_modify=None,
            content_delete=None, content_combined=None, main_intent_classification_details=None, sub_intent_classification_details=None,
            sql_generation_details=None, sql_execution_details=None, query_formatting_details=None, operation_response_details=None,
            is_phi_present=False, sql_string_for_execution=None, last_executed_sql_node=None, last_successful_execution_data=None,
            llm_call_history_for_intent_classification=[], llm_call_history_for_data_operations=[], user_feedback_history=[]
        )
        initial_state_dict = dict(initial_state)

        # --- 调用图 ---
        config = {"configurable": {"thread_id": "test-analysis-thread-1"}}
        final_state_dict = compiled_app.invoke(initial_state_dict, config=config)
        final_state = GraphState(**final_state_dict)

        # --- 断言 ---
        assert final_state.get("final_answer") == expected_analytical_answer
        assert final_state.get("error_message") is None, f"期望没有错误，但得到: {final_state.get('error_message')}"

        mock_classify_main_intent.assert_called_once()
        # 确认 classify_main_intent 的输入
        assert mock_classify_main_intent.call_args[0][0] == initial_user_query

        mock_classify_query_analysis_intent.assert_called_once()
        # 确认 classify_query_analysis_intent 的输入
        assert mock_classify_query_analysis_intent.call_args[0][0] == initial_user_query
        
        mock_generate_analysis_sql.assert_called_once()
        # 确认 generate_analysis_sql 的输入
        # (user_query, schema, table_names, data_sample)
        assert mock_generate_analysis_sql.call_args[0][0] == initial_user_query
        assert mock_generate_analysis_sql.call_args[0][1] == MOCK_SCHEMA_JSON_STRING
        assert mock_generate_analysis_sql.call_args[0][2] == MOCK_TABLE_NAMES
        # data_sample 在 GraphState 中是 JSON 字符串
        assert mock_generate_analysis_sql.call_args[0][3] == json.dumps({"users": [{"id": 1, "name": "Bob"}, {"id": 2, "name": "Alice"}]})

        mock_execute_sql_query.assert_called_once_with(expected_sql_for_assertion)
        
        mock_analyze_analysis_result.assert_called_once()
        # 确认 analyze_analysis_result 的输入
        # (user_query, sql_result, schema, table_names)
        assert mock_analyze_analysis_result.call_args[0][0] == initial_user_query
        assert mock_analyze_analysis_result.call_args[0][1] == json.dumps(mock_db_results) # API Client 返回的是 Python 对象，但Action中会转为JSON字符串存入状态
        assert mock_analyze_analysis_result.call_args[0][2] == MOCK_SCHEMA_JSON_STRING
        assert mock_analyze_analysis_result.call_args[0][3] == MOCK_TABLE_NAMES
        
        print("test_analysis_query_count_success 已通过。")

def test_query_no_result_found(compiled_app):
    """
    测试 2.3: SELECT 查询执行成功，但数据库返回空结果集。
    - Mock classify_main_intent -> query_analysis
    - Mock classify_query_analysis_intent -> query
    - Mock generate_select_sql 服务 -> 有效的 SELECT SQL 字符串
    - Mock api_client.execute_query -> 返回空列表 []
    - 验证图是否正确路由，并由实际的 handle_query_not_found_action 设置 final_answer 和 error_flag。
    """
    initial_user_query = "查找不存在的用户"

    with patch('langgraph_crud_app.services.llm.llm_query_service.classify_main_intent') as mock_classify_main_intent, \
         patch('langgraph_crud_app.services.llm.llm_query_service.classify_query_analysis_intent') as mock_classify_query_analysis_intent, \
         patch('langgraph_crud_app.services.llm.llm_query_service.generate_select_sql') as mock_generate_select_sql_service, \
         patch('langgraph_crud_app.services.api_client.execute_query') as mock_api_execute_query:

        # --- 设置 Mock 返回值 ---
        mock_classify_main_intent.return_value = {
            "intent": "query_analysis", "confidence": 0.99, "details": "用户想要查询数据。",
            "matched_keywords": ["查找"], "main_intent_debug_log": "主意图分类调试日志 for no result test"
        }
        mock_classify_query_analysis_intent.return_value = "query" # 子意图是查询
        
        # llm_query_service.generate_select_sql 服务应该直接返回 SQL 字符串
        expected_sql_from_llm_service = "SELECT * FROM users WHERE name = '不存在的用户';"
        mock_generate_select_sql_service.return_value = expected_sql_from_llm_service

        # 关键: 模拟数据库API返回空列表
        mock_api_execute_query.return_value = [] 

        # --- 执行图 ---
        inputs = {
            "user_query": initial_user_query,
            "current_flow_step": "test_query_no_result_found_input",
            "max_data_fetch_retries": 1, 
            "max_llm_call_retries": 1,
            "biaojiegou_save": "users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)", 
            "table_names": ["users"],
            "data_sample": "{'users': [{'id': 1, 'name': 'Alice', 'email': 'alice@example.com'}]}"
        }
        
        config = {"configurable": {"thread_id": "test-query-no-result-thread-v3"}} # New thread_id
        result = compiled_app.invoke(inputs, config=config)
        
        # --- 验证 ---
        # 1. 验证外部服务调用情况
        mock_classify_main_intent.assert_called_once_with(initial_user_query)
        mock_classify_query_analysis_intent.assert_called_once_with(initial_user_query)
        
        # generate_select_sql_action 节点会调用 llm_query_service.generate_select_sql
        # 我们需要验证这个服务被调用时的参数 (user_query, schema, table_names, data_sample)
        # 注意：data_sample 在 GraphState 中是 JSON 字符串，传递给服务时也应是 JSON 字符串
        mock_generate_select_sql_service.assert_called_once_with(
            initial_user_query,
            inputs["biaojiegou_save"],
            inputs["table_names"],
            inputs["data_sample"] 
        )
        
        # execute_sql_query_action 内部会调用 clean_sql_action, 其输出（通常与输入相同或带分号）
        # 会被存入 state["sql_string_for_execution"]
        # 然后 execute_sql_query_action 调用 api_client.execute_query 
        # api_client.execute_query 的参数只有一个位置参数: query
        # 假设 clean_sql_action 的行为是确保 SQL 带分号，或者至少不移除我们 mock 的 SQL 中的分号
        # 日志显示 clean_sql_action 输出了 "SELECT * FROM users WHERE name = '不存在的用户';"
        expected_sql_for_api_call = "SELECT * FROM users WHERE name = '不存在的用户';"
        mock_api_execute_query.assert_called_once_with(expected_sql_for_api_call)


        # 2. 验证最终状态是否由 handle_query_not_found_action 正确设置
        expected_final_answer = "没有找到您想查找的数据，请尝试重新输入或提供更完整的编号。"
        actual_final_answer = result.get("final_answer")
        
        print(f"Expected final_answer: '{expected_final_answer}'")
        print(f"Actual final_answer:   '{actual_final_answer}'")
        # print(f"Result state: {result}") # 太多内容，暂时注释

        assert actual_final_answer == expected_final_answer, \
               f"Final answer mismatch. Expected: '{expected_final_answer}', Got: '{actual_final_answer}'"
        assert result.get("error_flag") is True, "error_flag 应为 True 当查询无结果时"
        
        expected_error_message = "查询成功，但未找到匹配数据。"
        actual_error_message = result.get("error_message")
        assert actual_error_message == expected_error_message, \
               f"Error message mismatch. Expected: '{expected_error_message}', Got: '{actual_error_message}'"
        
        print("test_query_no_result_found 已通过。")

# TODO: 从 TEXT_PLAN.txt 为其他查询/分析场景添加更多测试:
# 2.4. SQL 生成失败
# 2.5. SQL 执行失败 (API error)
# ... 其他流程
