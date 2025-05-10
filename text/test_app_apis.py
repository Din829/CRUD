import pytest
import json
import pymysql # 用于模拟特定的 pymysql 错误
import os
from unittest.mock import patch, MagicMock

# 将项目根目录添加到 sys.path 以便导入 app
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app # 从项目的 app.py 导入 Flask app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # 将应用中的异常传播到测试客户端
    app.config['PROPAGATE_EXCEPTIONS'] = True
    with app.test_client() as client:
        yield client

# 如有必要，可以为测试模拟数据库连接详情，
# 或者确保测试环境指向一个测试数据库。
# 对于这些测试，我们假设数据库连接的环境变量已设置，
# 或者如果需要，我们可以在测试中覆盖它们。

# ======== /get_schema 端点测试 ========

def test_get_schema_success(client):
    """
    测试用例 1.1: 成功获取 schema。
    验证响应状态码 (200) 以及返回的 JSON 结构符合预期。
    假设数据库中存在一些表 (例如 users, prompts, api_tokens)。
    """
    response = client.get('/get_schema')
    assert response.status_code == 200
    data = json.loads(response.data)

    assert 'result' in data
    assert isinstance(data['result'], list)
    assert len(data['result']) == 1 # 预期列表中只有一个 JSON 字符串
    
    schema_str = data['result'][0]
    assert isinstance(schema_str, str)
    
    schema = json.loads(schema_str)
    assert isinstance(schema, dict)
    
    # 检查预期的表是否存在 (假设这些表是基于 CSV 文件创建的)
    # 这些名称应与数据库中的完全一致
    expected_tables = ['users', 'prompts', 'api_tokens'] 
    for table_name in expected_tables:
        assert table_name in schema, f"表 '{table_name}' 在 schema 中未找到"
        assert 'fields' in schema[table_name]
        assert isinstance(schema[table_name]['fields'], dict)
        assert 'foreign_keys' in schema[table_name] # 根据 app.py 的逻辑

    # 示例: 检查 'users' 表中的特定字段
    if 'users' in schema:
        assert 'id' in schema['users']['fields']
        assert 'username' in schema['users']['fields']
        assert 'email' in schema['users']['fields']
        # 如果已知字段类型，可以检查，例如 id 的类型可能是 'int(11)'
        # assert schema['users']['fields']['id']['type'] == 'int(11)' # 这可能非常依赖于数据库引擎


def test_get_schema_db_connection_error(client, mocker):
    """
    测试用例 1.2: 模拟数据库连接失败。
    验证是否返回适当的错误状态码 (例如 500) 和错误信息。
    """
    # Mock app.py 中的 get_db_connection 上下文管理器
    # 方法 1: Mock pymysql.connect 使其抛出错误
    mocker.patch('pymysql.connect', side_effect=pymysql.err.OperationalError("模拟的数据库连接错误"))
    
    # 方法 2: 如果 get_db_connection 本身很复杂, 可以 mock 它的 __enter__ 或它 yield 的连接对象
    # 为简单起见, 如果 get_db_connection 直接使用 pymysql.connect, mock pymysql.connect 通常足够直接。

    response = client.get('/get_schema')
    assert response.status_code == 500
    data = json.loads(response.data)
    assert 'error' in data
    # 确切的错误消息可能因 pymysql 而异，但它应包含核心信息
    # 在 app.py 中, 它返回 jsonify({"error": str(e)}), 所以我们期望错误的字符串表示形式
    assert "模拟的数据库连接错误" in str(data['error'])

# 注意: 为了让这些测试正确运行:
# 1. 必须有一个正在运行的 MySQL 服务器，并且可以通过环境变量中定义的凭据进行访问
#    (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)。
# 2. 在运行 `test_get_schema_success` 之前，测试数据库 (DB_NAME) 应已创建并填充了表
#    (例如 'users', 'prompts', 'api_tokens')。
#    一个设置脚本或 fixture 可以处理此数据库初始化。
# 3. 如果 app.py 不在根目录，请相应调整 sys.path。
#    添加的 sys.path.insert 假设 'app.py' 位于 'text/' 的父目录中。
#    如果 `text/` 与 `app.py` 在同一级别，那么如果 `tests` 是一个合适的 Python 包 (带有 __init__.py)，
#    则 `from ..app import app` 会更典型。
#    考虑到在 `text/` 中创建文件的请求，sys.path 操作是一种常见的变通方法。

# 如何运行这些测试:
# 导航到包含 `text/` 和 `app.py` 的目录 (例如 DifyLang/)
# 确保已设置数据库的环境变量。
# 运行: pytest text/test_app_apis.py 