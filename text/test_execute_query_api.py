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
    app.config['PROPAGATE_EXCEPTIONS'] = True # 在测试中，通常希望异常传播以便 pytest 可以捕获它们
    # app.config['TRAP_HTTP_EXCEPTIONS'] = False # 如果设置为 True, HTTP 异常会变成 Python 异常
    # app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False # 如果为 True, 异常后上下文不会被销毁
    with app.test_client() as client:
        yield client

# 注意：运行这些测试需要一个配置好的数据库环境。
# 测试会实际连接到数据库执行 SELECT 查询。
# 请确保环境变量（DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME）已设置，
# 或者 app.py 中的默认连接参数指向一个可用的测试数据库。
# 测试数据库中需要有 'users', 'prompts', 'api_tokens' 等表，并且包含一些数据用于测试。

# ======== /execute_query 端点测试 ========

# --- 辅助数据和函数 ---
# 假设我们有基于 users.csv, prompts.csv, api_tokens.csv 的数据
# 例如，users 表至少有一条记录，方便测试单表查询

def test_execute_query_success_select_single_table(client):
    """
    测试用例 2.1 (部分): 有效的 SELECT 查询（单表）。
    验证状态码 (200) 和查询结果。
    """
    # 假设 'users' 表存在且至少有一条记录
    response = client.post('/execute_query', json={'sql_query': 'SELECT id, username FROM users LIMIT 1;'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) >= 0 # 可以是0或更多，取决于表内容
    if len(data) > 0:
        assert 'id' in data[0]
        assert 'username' in data[0]

def test_execute_query_success_select_multi_table_join(client):
    """
    测试用例 2.1 (部分): 有效的 SELECT 查询（多表连接）。
    验证状态码 (200) 和查询结果。
    假设 'prompts' 表和 'users' 表可以通过 user_id 连接。
    """
    # 确保 prompts 表和 users 表都存在，并且可以通过 user_id 连接
    # 并且至少有一条匹配的记录
    query = """
    SELECT p.id as prompt_id, p.title, u.username 
    FROM prompts p 
    JOIN users u ON p.user_id = u.id 
    LIMIT 1;
    """
    response = client.post('/execute_query', json={'sql_query': query})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    if len(data) > 0:
        assert 'prompt_id' in data[0]
        assert 'title' in data[0]
        assert 'username' in data[0]

def test_execute_query_select_empty_result(client):
    """
    测试用例 2.2: SELECT 查询返回空结果集。
    验证状态码 (200) 和返回空列表 []。
    """
    # 使用一个几乎肯定不会返回结果的查询条件
    response = client.post('/execute_query', json={'sql_query': "SELECT * FROM users WHERE username = 'THIS_USER_SHOULD_NOT_EXIST_IN_TEST_DB_12345';"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 0

def test_execute_query_non_select_statement_forbidden(client):
    """
    测试用例 2.3: 无效的 SQL 语法（例如，非 SELECT 语句如 UPDATE、DELETE）。
    验证是否返回禁止操作的错误 (例如 403)。
    """
    non_select_queries = [
        'UPDATE users SET username = \'test\' WHERE id = 1;',
        'DELETE FROM users WHERE id = 1;',
        'INSERT INTO users (username) VALUES (\'test\');'
    ]
    for query in non_select_queries:
        response = client.post('/execute_query', json={'sql_query': query})
        assert response.status_code == 403 # app.py 中定义的只允许 SELECT
        data = json.loads(response.data)
        assert 'error' in data
        assert "Only SELECT queries are allowed" in data['error']

def test_execute_query_sql_syntax_error(client):
    """
    测试用例 2.4: SQL 语法错误 (例如，拼写错误的表名/列名)。
    验证是否返回数据库层面的错误 (例如 500 及错误详情)。
    """
    # 'userz' 是一个不存在的表名 (假设)
    # 'idd' 是一个不存在的列名 (假设)
    error_queries = [
        'SELECT * FROM userz;', # 错误表名
        'SELECT idd FROM users;'  # 错误列名
    ]
    for query in error_queries:
        response = client.post('/execute_query', json={'sql_query': query})
        assert response.status_code == 500 # 期望数据库错误导致 500
        data = json.loads(response.data)
        assert 'error' in data
        # 错误信息可能包含 "1064" (MySQL语法错误) 或 "1146" (表不存在) 或 "1054" (未知列)
        # e.g., data['error'] might be a tuple like [1146, "Table 'your_db.userz' doesn't exist"]
        #       or [1054, "Unknown column 'idd' in 'field list'"]
        # 我们只检查它是一个列表或元组（因为 app.py 中 e.args 被返回）
        assert isinstance(data['error'], (list, tuple)) 
        # 并且包含至少一个元素
        assert len(data['error']) > 0 


def test_execute_query_empty_or_semicolon_only(client):
    """
    测试用例 2.5: 空查询字符串或只有分号的查询。
    验证错误处理 (例如 400)。
    """
    empty_queries = [
        '',
        ';',
        '   ',
        '  ;  ',
        ';;;;'
    ]
    for query in empty_queries:
        response = client.post('/execute_query', json={'sql_query': query})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        # 错误消息可能是 "No SQL query provided" 或 "Empty SQL query after processing"
        assert "query provided" in data['error'] or "query after processing" in data['error']

def test_execute_query_sql_injection_attempt_basic_select_only(client):
    """
    测试用例 2.6: 针对性的 SQL 注入尝试。
    验证参数化是否有效（预期是查询因语法错误而失败，或只执行 SELECT 部分，而不是执行恶意代码）。
    由于 /execute_query 只允许 SELECT，这里主要测试是否能绕过 SELECT 限制。
    """
    # 尝试通过分号执行多条语句 (期望被 app.py 中的 SELECT 检查或 SQL 解析器阻止)
    # 或者，如果查询被清理后只剩下 SELECT 部分，那也是一种形式的保护
    # 这个测试的核心是确保非 SELECT 部分不会被执行
    
    # 1. 尝试在 SELECT 后附加恶意命令
    injection_query_suffix = "SELECT id FROM users; DROP TABLE users;"
    response_suffix = client.post('/execute_query', json={'sql_query': injection_query_suffix})
    
    # 预期行为：
    # 1. 如果 app.py 严格只取分号前的第一个 SELECT，则 DROP 不会被执行，SELECT 可能成功或因后续语法失败。
    # 2. 如果 app.py 允许了带分号的 SELECT 但数据库驱动只执行第一句，则 SELECT 成功，DROP 不执行。
    # 3. 如果 app.py 尝试执行整个字符串但数据库配置为不允许复合语句，则可能语法错误。
    # 4. 如果 app.py 的 `startswith('SELECT')` 检查足够健壮，则此查询本身就会被 403 拒绝（如果它认为这不是一个合法的 SELECT 开头）。
    #    app.py 的逻辑是: 清理 -> 检查 SELECT -> 加回分号 (如果原来有)。
    #    所以 "SELECT id FROM users; DROP TABLE users;" 清理后是 "SELECT id FROM users; DROP TABLE users"
    #    这仍然以 SELECT 开头，所以会通过 403 检查。然后它会尝试执行。
    #    此时，行为取决于数据库驱动是否允许执行多语句。通常，PyMySQL 默认不允许多语句。

    # 验证 users 表仍然存在 (间接证明 DROP TABLE 未执行)
    # 为了确切验证，我们可以在测试前后检查表是否存在，或者检查返回的数据。
    # 如果 DROP 执行了，后续的 'SELECT * FROM users' 会失败。
    
    # 假设 PyMySQL 不执行多语句，或者只执行第一句
    if response_suffix.status_code == 200:
        # SELECT 部分可能成功了
        data_suffix = json.loads(response_suffix.data)
        assert isinstance(data_suffix, list) # 确认是 SELECT 的结果
    elif response_suffix.status_code == 500:
        # 可能是数据库层面的错误，比如 "Commands out of sync" 或多语句被禁止
        data_suffix = json.loads(response_suffix.data)
        assert 'error' in data_suffix
        # 错误应该是一个元组或列表，第一个元素是错误代码
        assert isinstance(data_suffix['error'], (list, tuple)), \
            f"Expected error to be a list or tuple, got {type(data_suffix['error'])}"
        assert len(data_suffix['error']) >= 2, \
            f"Expected error to have at least 2 elements, got {len(data_suffix['error'])}"
        
        error_code = data_suffix['error'][0]
        error_message = str(data_suffix['error'][1]).upper()

        # 我们期望一个语法错误 (1064) 因为整个多语句被视为一个非法语句
        assert error_code == 1064, f"Expected error code 1064, got {error_code}"
        # 语法错误消息应该会提到它在哪里卡住了，即 'DROP TABLE USERS'
        assert "DROP TABLE" in error_message, \
            f"Expected 'DROP TABLE' in error message, got '{error_message}'"
        assert "NEAR 'DROP TABLE USERS'" in error_message, \
            f"Expected error message to specify near 'DROP TABLE USERS', got '{error_message}'"
    else:
        # 如果是 403，说明 SELECT 检查逻辑可能更严格地处理了这种情况
        # 这对于当前 app.py 的 SELECT startswith 检查逻辑来说不太可能，因为查询确实以 SELECT 开头
        pytest.fail(f"Unexpected status code {response_suffix.status_code}. Expected 200 or 500.")

    # 再次查询 users 表以确认其存在，这是一个很好的验证方法，
    # 但它依赖于测试数据库在测试之间不会被其他测试意外修改。
    # 这里我们简单地假设如果前面的注入测试没有以非预期方式通过（比如返回200且users表没了），
    # 或者以预期的错误方式失败（500语法错误），那么表结构是安全的。
    verify_users_table_exists = client.post('/execute_query', json={'sql_query': 'SELECT COUNT(*) FROM users;'})
    assert verify_users_table_exists.status_code == 200, \
        "Failed to query users table after injection attempt, it might have been dropped or access lost."

    # 2. 尝试注释掉部分查询
    injection_query_comment = "SELECT id FROM users WHERE username = 'admin' -- ' OR 1=1;"
    # 预期: -- 后面的内容被视为注释，查询会变成 "SELECT id FROM users WHERE username = 'admin'"
    response_comment = client.post('/execute_query', json={'sql_query': injection_query_comment})
    assert response_comment.status_code == 200, \
        f"Expected status 200 for commented query, got {response_comment.status_code}. Error: {response_comment.data.decode() if response_comment.status_code != 200 else ''}"
    # 可选：进一步验证返回的数据是否符合预期，例如只返回 'admin' 用户的数据（如果存在）
    # data_comment = json.loads(response_comment.data)
    # if 'admin_user_exists_in_test_db': # 这个需要根据实际测试数据来判断
    #    assert len(data_comment) == 1
    #    assert data_comment[0]['username'] == 'admin'
    # else:
    #    assert len(data_comment) == 0

    # 注意：更完善的SQL注入测试会更复杂，并可能需要模拟数据库的特定响应。
    # 对于 /execute_query，由于其仅限 SELECT，主要的风险是信息泄露，而不是数据修改。
    # app.py 的实现通过严格检查查询以 `SELECT` 开头来阻止修改性语句。
    # `cursor.execute()` 本身通常会处理参数化，但这里我们直接传递了SQL字符串。
    # PyMySQL 默认情况下，`cursor.execute()` 不支持一次执行多个以分号分隔的语句。
    # 它通常会执行第一个语句，或者如果配置/驱动支持，可能会抛出错误。
    # 因此，注入 "SELECT ...; DROP ..." 通常会导致 DROP 不被执行。

    # 更重要的检查是确保 e.g. `sql_query = "SELECT * FROM users WHERE id = " + user_input` 这种直接拼接永远不会发生。
    # 在当前 /execute_query 的设计中，整个 SQL 是由外部（LLM）构建的，所以应用层参数化的概念不同。
    # 安全性依赖于：
    # 1. LLM 不会生成恶意的非 SELECT 语句（被 `startswith('SELECT')` 阻止）。
    # 2. 数据库连接不允许执行多语句，或只执行第一条 SELECT。
    # 3. 返回的数据不会意外泄露不应显示的信息（这是LLM格式化输出的责任）。
    pass # 占位符，表示测试用例结构完成 