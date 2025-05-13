import pytest
import json
from unittest.mock import patch, MagicMock, call
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

# TODO: 从 TEXT_PLAN.txt 为其他查询/分析场景添加更多测试:
# - 2.2. 分析查询 (例如 COUNT(*))
# - 2.3. 查询无结果
# - 2.4. SQL 生成失败
# - 2.5. SQL 执行失败
# TODO: 修复 pydantic 警告（在 langgraph_crud_app/services/llm/__init__.py 中将 langchain_core.pydantic_v1 替换为 pydantic 或 pydantic.v1）