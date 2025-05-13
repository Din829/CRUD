import pytest
import json
import pymysql # 仍然需要导入以模拟其特定错误类型
import sqlite3 # 新增：导入 sqlite3 用于测试数据库连接
import os
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
import re # 导入 re 用于解析 DESCRIBE

# 将项目根目录添加到 sys.path 以便导入 app
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from app import app, get_db_connection # 显式导入 get_db_connection 以便 patch

# 定义测试数据库文件路径 和 schema 文件路径
TEST_DB_PATH = os.path.join(project_root, 'test_db_data', 'test_app.db')
SCHEMA_FILE_PATH = os.path.join(project_root, 'text', '表结构.txt')

# --- 预加载 Schema 定义，用于 Mock DESCRIBE --- 
EXPECTED_SCHEMA_FROM_FILE = {}
if os.path.exists(SCHEMA_FILE_PATH):
    with open(SCHEMA_FILE_PATH, 'r', encoding='utf-8') as f_schema:
        EXPECTED_SCHEMA_FROM_FILE = json.load(f_schema)
else:
    print(f"警告: Schema 文件 {SCHEMA_FILE_PATH} 未找到，DESCRIBE mock 可能不准确。")

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['PROPAGATE_EXCEPTIONS'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def mock_db(mocker):
    """Mock app.get_db_connection，使其模拟 MySQL 的 SHOW/DESCRIBE 行为，并将其他操作代理到 SQLite。"""
    real_sqlite_conn = None
    # 用于存储模拟 SHOW/DESCRIBE 的结果
    mock_query_results = None 

    @contextmanager
    def mock_cursor_manager(sqlite_conn_actual):
        nonlocal mock_query_results
        # 创建一个真实的 SQLite cursor，用于代理非 SHOW/DESCRIBE 命令
        real_sqlite_cursor = sqlite_conn_actual.cursor()
        
        # 创建一个 MagicMock 对象来模拟 pymysql 的 cursor
        mocked_cursor = MagicMock(spec=pymysql.cursors.DictCursor) # 或者 pymysql.cursors.Cursor

        def custom_execute(sql_query, params=None):
            nonlocal mock_query_results
            print(f"[Mock Cursor] execute() called with SQL: {sql_query[:200]}") # 打印 SQL 前缀
            sql_lower = sql_query.strip().lower()
            
            if sql_lower == "show tables":
                # 模拟 SHOW TABLES 的结果
                # app.py 期望的格式: [{'Tables_in_db_name': 'table_name'}, ...]
                # 我们需要从 TEST_DB_PATH 中提取模拟的数据库名，或者用一个占位符
                db_name_placeholder = os.path.basename(TEST_DB_PATH) # 使用文件名作为占位符
                mock_query_results = [
                    {f'Tables_in_{db_name_placeholder}': table_name} 
                    for table_name in EXPECTED_SCHEMA_FROM_FILE.keys()
                ]
                print(f"[Mock Cursor] Mocking SHOW TABLES. Results: {mock_query_results}")
                return # SHOW TABLES 不返回行数
            
            # 使用正则表达式匹配 DESCRIBE `table_name`
            describe_match = re.match(r"describe\s+`?([a-zA-Z0-9_]+)`?", sql_lower)
            if describe_match:
                table_name = describe_match.group(1)
                if table_name in EXPECTED_SCHEMA_FROM_FILE and 'fields' in EXPECTED_SCHEMA_FROM_FILE[table_name]:
                    # 模拟 DESCRIBE 的结果
                    # app.py 期望的格式: [{'Field': ..., 'Type': ..., 'Null': ..., 'Key': ..., 'Default': ...}, ...]
                    mock_query_results = []
                    for field, details in EXPECTED_SCHEMA_FROM_FILE[table_name]['fields'].items():
                        mock_query_results.append({
                            'Field': field,
                            'Type': details.get('type', 'TEXT'),
                            'Null': details.get('null', 'YES'),
                            'Key': details.get('key', ''),
                            'Default': details.get('default', None), # pymysql 可能返回 None
                            # 'Extra': details.get('extra', '') # 如果需要 Extra
                        })
                    print(f"[Mock Cursor] Mocking DESCRIBE {table_name}. Results count: {len(mock_query_results)}")
                else:
                    print(f"[Mock Cursor] DESCRIBE target table '{table_name}' not in EXPECTED_SCHEMA_FROM_FILE.")
                    mock_query_results = [] # 返回空结果，模拟表不存在
                return
            
            # 对于所有其他 SQL 语句，代理到真实的 SQLite cursor
            print(f"[Mock Cursor] Proxying to SQLite cursor: {sql_query[:100]}")
            if params:
                return real_sqlite_cursor.execute(sql_query, params)
            else:
                return real_sqlite_cursor.execute(sql_query)

        def custom_fetchall():
            nonlocal mock_query_results
            print(f"[Mock Cursor] fetchall() called.")
            if mock_query_results is not None:
                # 返回为 SHOW/DESCRIBE 准备的模拟结果
                results_to_return = list(mock_query_results) # 复制列表以防意外修改
                mock_query_results = None # 清空，以便下次 execute 正确工作
                print(f"[Mock Cursor] Returning mocked results for fetchall(): {len(results_to_return)} rows")
                return results_to_return
            else:
                # 代理到真实的 SQLite cursor
                print("[Mock Cursor] Proxying fetchall() to SQLite cursor.")
                return real_sqlite_cursor.fetchall()
        
        mocked_cursor.execute = custom_execute
        mocked_cursor.fetchall = custom_fetchall
        # 如果 app.py 用到了 cursor.rowcount, cursor.lastrowid 等，也需要模拟
        # mocked_cursor.rowcount = real_sqlite_cursor.rowcount # 这样直接赋值可能不行，需要 property 或 side_effect
        # 简单起见，暂时不完整模拟所有 cursor 属性，只关注 execute 和 fetchall

        try:
            yield mocked_cursor # 返回配置好的 Mock Cursor
        finally:
            # mocked_cursor 不需要关闭，real_sqlite_cursor 由其连接管理
            pass 

    @contextmanager
    def mock_connection_manager():
        nonlocal real_sqlite_conn
        try:
            real_sqlite_conn = sqlite3.connect(TEST_DB_PATH)
            real_sqlite_conn.row_factory = sqlite3.Row # 确保 SQLite 返回类似字典的行
            real_sqlite_conn.execute("PRAGMA foreign_keys = ON")
            
            mock_pymysql_conn = MagicMock(spec=pymysql.connections.Connection)
            mock_pymysql_conn.cursor.return_value = mock_cursor_manager(real_sqlite_conn) # 返回支持 with 的 mock cursor manager
            mock_pymysql_conn.commit.side_effect = real_sqlite_conn.commit
            mock_pymysql_conn.rollback.side_effect = real_sqlite_conn.rollback
            mock_pymysql_conn.close.side_effect = real_sqlite_conn.close
            # 模拟 db 属性 (bytes) 以匹配 app.py 中可能的用法
            mock_pymysql_conn.db = os.path.basename(TEST_DB_PATH).encode('utf-8') 

            print(f"[Fixture mock_db] Yielding Mock PyMySQL Connection wrapping SQLite to {TEST_DB_PATH}")
            yield mock_pymysql_conn
        finally:
            if real_sqlite_conn:
                print("[Fixture mock_db] Closing real SQLite connection")
                real_sqlite_conn.close()
                real_sqlite_conn = None

    patched_manager = mocker.patch('app.get_db_connection', return_value=mock_connection_manager())
    yield patched_manager

# ======== /get_schema 端点测试 ========

def test_get_schema_success(client):
    """
    测试用例 1.1: 成功获取 schema。
    Mock 层现在应该能正确处理 SHOW TABLES 和 DESCRIBE。
    """
    response = client.get('/get_schema')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'result' in data
    assert isinstance(data['result'], list)
    assert len(data['result']) == 1
    schema_str = data['result'][0]
    assert isinstance(schema_str, str)
    schema_from_api = json.loads(schema_str)
    assert isinstance(schema_from_api, dict)
    
    # 与从文件加载的预期 Schema 进行比较
    # 注意: app.py 中的 /get_schema 可能会对表名和字段名的大小写进行处理
    # 或者返回的结构可能与文件略有差异，需要精确匹配或灵活比较
    # 这里我们假设格式基本一致
    assert len(schema_from_api.keys()) == len(EXPECTED_SCHEMA_FROM_FILE.keys())
    for table_name, table_details_expected in EXPECTED_SCHEMA_FROM_FILE.items():
        assert table_name in schema_from_api, f"表 '{table_name}' 未在 API 返回的 schema 中找到"
        table_details_api = schema_from_api[table_name]
        assert 'fields' in table_details_api
        # 比较字段数量
        assert len(table_details_api['fields']) == len(table_details_expected['fields'])
        for field_name, field_details_expected in table_details_expected['fields'].items():
            assert field_name in table_details_api['fields'], f"字段 '{field_name}' 未在表 '{table_name}' 的 API schema 中找到"
            field_details_api = table_details_api['fields'][field_name]
            # 比较字段的关键属性 (Type, Null, Key, Default)
            assert field_details_api.get('type') == field_details_expected.get('type')
            assert field_details_api.get('null') == field_details_expected.get('null')
            assert field_details_api.get('key') == field_details_expected.get('key')
            # 假设 'default' 键也需要这个修正,与模式保持一致。
            # 问题报告提到: "# Default 的比较可能仍需注意 None vs null 的细微差别，但键名应为小写"
            # "# assert field_details_api.get('default') == field_details_expected.get('default')"
            # 所以,如果这行代码存在 'Default',应该改为 'default'。
            # 如果 'Default' 的原始行不同或比较 None,那个特定的逻辑应该保留
            # 但对 field_details_api 的键访问应该是 'default'。
            # 目前,假设与其他字段保持直接的并行关系:
            original_default_api = field_details_api.get('default')
            original_default_expected = field_details_expected.get('default')

            # Handle potential None from .get() if 'default' key is missing, and db 'Default' can be None
            if original_default_expected is None:
                assert original_default_api is None or original_default_api == '' or original_default_api == 'NULL' # Adjust as per actual possible 'None' representations
            else:
                assert original_default_api == original_default_expected

def test_get_schema_db_connection_error(client, mocker):
    """
    测试用例 1.2: 模拟数据库连接失败。
    """
    mock_context = MagicMock()
    mock_context.__enter__.side_effect = pymysql.err.OperationalError("模拟的数据库连接错误(SQLite测试)")
    mocker.patch('app.get_db_connection', return_value=mock_context)
    response = client.get('/get_schema')
    assert response.status_code == 500
    data = json.loads(response.data)
    assert 'error' in data
    assert "模拟的数据库连接错误(SQLite测试)" in str(data['error'])

# 注意:
# 1. 这个设置假设 `init_test_db.py` 在 `pytest` 命令运行之前已经被 CI 流程执行。
# 2. `test_get_schema_success` 依赖于 `init_test_db.py` 创建的表的实际结构。
# 3. /get_schema 端点本身的兼容性仍需关注 (DESCRIBE vs PRAGMA table_info)。

# 如何运行这些测试:
# 1. 手动运行 `python scripts/init_test_db.py`