import sys
import os

# 将项目根目录添加到 sys.path
# 假设此测试文件位于 DifyLang/text/test_delete_record_api.py
# 并且 app.py 和 database_utils.py 位于 DifyLang/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import csv
import shutil
from flask import Flask
from app import app as flask_app, get_db_connection

# 定义测试数据的相对路径
CSV_FILES_DIR = os.path.join(os.path.dirname(__file__), '') # CSV 文件在 tests 目录下
USERS_CSV = os.path.join(CSV_FILES_DIR, 'users.csv')
PROMPTS_CSV = os.path.join(CSV_FILES_DIR, 'prompts.csv')
API_TOKENS_CSV = os.path.join(CSV_FILES_DIR, 'api_tokens.csv')

TABLE_PRIMARY_KEYS = {
    'users': 'id',
    'prompts': 'id',
    'api_tokens': 'id'
}

def get_table_columns(conn, table_name):
    """获取表的列名，处理可能的 BOM 字符。"""
    cursor = conn.cursor()
    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
    columns = [row['Field'] for row in cursor.fetchall()]
    # 清理列名中的 BOM 字符
    cleaned_columns = [col.lstrip('\ufeff').lstrip('﻿') for col in columns]
    return cleaned_columns

def load_csv_to_db(conn, csv_path, table_name):
    """将 CSV 文件数据加载到数据库表中。"""
    if not os.path.exists(csv_path):
        print(f"CSV file not found: {csv_path}")
        return

    with open(csv_path, 'r', encoding='utf-8-sig') as f: # 使用 utf-8-sig 读取以处理BOM
        reader = csv.DictReader(f)
        fieldnames = [name.lstrip('\ufeff').lstrip('﻿') for name in reader.fieldnames] # 清理表头
        
        # 获取数据库中的实际列名
        db_columns = get_table_columns(conn, table_name)
        
        # 过滤掉CSV中存在但数据库表中不存在的列
        valid_fieldnames = [name for name in fieldnames if name in db_columns]
        
        data_to_insert = []
        for row in reader:
            # 只选择有效的列进行插入
            filtered_row = {key.lstrip('\ufeff').lstrip('﻿'): value for key, value in row.items() if key.lstrip('\ufeff').lstrip('﻿') in valid_fieldnames}
            data_to_insert.append(filtered_row)

    if not data_to_insert:
        return

    # 确保插入语句中的列名与有效列名一致
    columns_str = ', '.join([f"`{col}`" for col in valid_fieldnames]) # 给列名加上反引号
    placeholders = ', '.join(['%s'] * len(valid_fieldnames))
    sql = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})" # 给表名加上反引号

    cursor = conn.cursor()
    for record in data_to_insert:
        values = [record.get(col) for col in valid_fieldnames]
        try:
            cursor.execute(sql, tuple(values))
        except Exception as e:
            print(f"Error inserting record into {table_name}: {record}")
            print(f"SQL: {sql}")
            print(f"Values: {values}")
            print(f"Error: {e}")
            raise
    conn.commit()
    cursor.close()

@pytest.fixture(scope='function')
def client():
    """提供 Flask 测试客户端。"""
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

@pytest.fixture(scope='function')
def db_setup_for_delete_tests(client):
    """
    在每个测试函数执行前清空并重新加载数据库。
    顺序：api_tokens, prompts, users (因为外键约束)
    加载顺序：users, prompts, api_tokens
    """
    # print("Setting up DB for delete tests...")
    with get_db_connection() as conn:
        try:
            cursor = conn.cursor()
            # 禁用外键检查
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
            
            # 清空表的顺序与外键约束相反
            tables_to_clear = ['api_tokens', 'prompts', 'users']
            for table in tables_to_clear:
                # print(f"Clearing table {table}...")
                cursor.execute(f"TRUNCATE TABLE `{table}`") # 给表名加上反引号
            conn.commit()
            
            # 启用外键检查
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
            conn.commit()
            # print("Tables cleared.")

            # 加载数据的顺序考虑外键依赖
            # print("Loading data from CSVs...")
            load_csv_to_db(conn, USERS_CSV, 'users')
            load_csv_to_db(conn, PROMPTS_CSV, 'prompts')
            load_csv_to_db(conn, API_TOKENS_CSV, 'api_tokens')
            # print("Data loaded.")
            
            # # ---- 调试代码开始 ----
            # print("\nDebug: Contents of 'users' table after loading in fixture:")
            # cursor.execute("SELECT * FROM `users`")
            # users_after_load = cursor.fetchall()
            # if users_after_load:
            #     for row in users_after_load:
            #         print(row)
            # else:
            #     print("'users' table is empty after loading.")
            # print("---- Debug: End of users table contents ----\n")
            # # ---- 调试代码结束 ----

        finally:
            if cursor: # 确保 cursor 存在才关闭
                cursor.close()
        # conn.close() # 由 with 语句处理
    
    # print("DB setup complete for delete tests.")
    yield client # 这里 yield client 是为了如果测试函数也需要 client fixture

# 接下来是测试用例

def test_delete_single_existing_record_by_id(client, db_setup_for_delete_tests):
    """测试 5.1: 成功删除存在的单条记录 (通过主键 ID)。"""
    table_name = "users"
    record_id_to_delete = 2 # 修改为 users.csv 中实际存在的 ID (e.g., Bob)

    # 1. 验证记录删除前确实存在
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM `{table_name}` WHERE id = %s", (record_id_to_delete,))
        record_before_delete = cursor.fetchone()
    assert record_before_delete is not None, f"记录 ID {record_id_to_delete} 在删除前未在表 {table_name} 中找到。"

    # 2. 执行删除操作
    response = client.post('/delete_record', json={
        'table_name': table_name,
        'primary_key': 'id',
        'primary_value': record_id_to_delete
    })

    # 3. 验证响应
    assert response.status_code == 200
    response_data = response.get_json()
    expected_message = f"Record with id={record_id_to_delete} deleted successfully"
    assert response_data['message'] == expected_message

    # 4. 验证记录在数据库中已被删除
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM `{table_name}` WHERE id = %s", (record_id_to_delete,))
        record_after_delete = cursor.fetchone()
    assert record_after_delete is None, f"记录 ID {record_id_to_delete} 在删除后仍然存在于表 {table_name} 中。"

def test_delete_non_existent_record_by_id(client, db_setup_for_delete_tests):
    """测试 5.2: 删除不存在的记录 (通过主键 ID)。"""
    table_name = "users"
    record_id_to_delete = 99999 # 一个数据库中肯定不存在的 ID

    # 1. 执行删除操作
    response = client.post('/delete_record', json={
        'table_name': table_name,
        'primary_key': 'id',
        'primary_value': record_id_to_delete
    })

    # 2. 验证响应
    assert response.status_code == 200 # API 对于未找到记录也返回 200
    response_data = response.get_json()
    expected_message = f"No record found with id={record_id_to_delete} in {table_name}, but operation completed successfully"
    assert response_data['message'] == expected_message

    # 3. （可选）验证记录在数据库中确实仍然不存在 (虽然它本来就不存在)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM `{table_name}` WHERE id = %s", (record_id_to_delete,))
        record_after_delete = cursor.fetchone()
    assert record_after_delete is None, f"尝试删除不存在的记录 ID {record_id_to_delete} 后，它不应该存在。"

def test_delete_multiple_records_by_shared_key(client, db_setup_for_delete_tests):
    """测试 5.3 (修订版): 删除 prompts 表中特定 user_id 的所有记录。"""
    table_name = "prompts"
    shared_key_column = "user_id" # 要作为删除条件的列名
    shared_key_value = 31         # user_id = 31 (nathan) 有两条 prompts

    # 1. 验证删除前，目标记录确实存在，并且有其他记录也存在
    prompts_for_user_before = []
    other_prompts_before_count = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 获取目标用户的所有 prompts
        cursor.execute(f"SELECT * FROM `{table_name}` WHERE `{shared_key_column}` = %s", (shared_key_value,))
        prompts_for_user_before = cursor.fetchall()
        assert len(prompts_for_user_before) == 2, f"用户 ID {shared_key_value} 在删除前应有 2 条 prompts，实际找到 {len(prompts_for_user_before)} 条。"
        
        # 获取其他用户的 prompts 总数，用于后续验证其他记录不受影响
        cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}` WHERE `{shared_key_column}` != %s", (shared_key_value,))
        other_prompts_before_count = cursor.fetchone()['count']
        assert other_prompts_before_count > 0, "数据库中应存在其他用户的 prompts 记录。"

    # 2. 执行删除操作
    response = client.post('/delete_record', json={
        'table_name': table_name,
        'primary_key': shared_key_column, # 使用 user_id 作为 "primary_key"
        'primary_value': shared_key_value
    })

    # 3. 验证响应
    assert response.status_code == 200
    response_data = response.get_json()
    # API 对于 affected_rows > 0 就返回这个消息，即使删了多行
    expected_message = f"Record with {shared_key_column}={shared_key_value} deleted successfully"
    assert response_data['message'] == expected_message

    # 4. 验证目标记录在数据库中已被删除
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM `{table_name}` WHERE `{shared_key_column}` = %s", (shared_key_value,))
        prompts_after_delete = cursor.fetchall()
        assert len(prompts_after_delete) == 0, f"用户 ID {shared_key_value} 的 prompts 在删除后仍然存在。"

        # 5. 验证其他用户的记录未受影响
        cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}` WHERE `{shared_key_column}` != %s", (shared_key_value,))
        other_prompts_after_count = cursor.fetchone()['count']
        assert other_prompts_after_count == other_prompts_before_count, "其他用户的 prompts 记录数量在删除操作后发生了变化。"

def test_delete_record_with_cascade(client, db_setup_for_delete_tests):
    """
    测试 5.4: 测试级联删除。
    删除 users 表中的记录 (id=2, bob)，验证其在 prompts 和 api_tokens 中的关联记录是否被删除。
    假设 prompts.user_id 和 api_tokens.user_id 外键已设置 ON DELETE CASCADE。
    """
    user_id_to_delete = 2
    user_table = "users"
    prompt_table = "prompts"
    api_token_table = "api_tokens"

    # 1. 验证删除前父记录和子记录都存在
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 验证用户
        cursor.execute(f"SELECT * FROM `{user_table}` WHERE id = %s", (user_id_to_delete,))
        user_record = cursor.fetchone()
        assert user_record is not None, f"用户 ID {user_id_to_delete} 在删除前未找到。"

        # 验证关联的 prompts (用户 Bob (id=2) 有 prompt id=21)
        cursor.execute(f"SELECT * FROM `{prompt_table}` WHERE user_id = %s", (user_id_to_delete,))
        prompts_before = cursor.fetchall()
        assert len(prompts_before) > 0, f"用户 ID {user_id_to_delete} 在删除前没有关联的 prompts 记录。"
        prompt_ids_before = [p['id'] for p in prompts_before]

        # 验证关联的 api_tokens (用户 Bob (id=2) 有 api_token id=2)
        cursor.execute(f"SELECT * FROM `{api_token_table}` WHERE user_id = %s", (user_id_to_delete,))
        tokens_before = cursor.fetchall()
        assert len(tokens_before) > 0, f"用户 ID {user_id_to_delete} 在删除前没有关联的 api_tokens 记录。"
        token_ids_before = [t['id'] for t in tokens_before]

    # 2. 执行删除父记录操作
    response = client.post('/delete_record', json={
        'table_name': user_table,
        'primary_key': 'id',
        'primary_value': user_id_to_delete
    })

    # 3. 验证删除父记录的响应
    assert response.status_code == 200
    response_data = response.get_json()
    expected_message = f"Record with id={user_id_to_delete} deleted successfully"
    assert response_data['message'] == expected_message

    # 4. 验证父记录和子记录在数据库中都已被删除
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 验证用户已被删除
        cursor.execute(f"SELECT * FROM `{user_table}` WHERE id = %s", (user_id_to_delete,))
        user_record_after = cursor.fetchone()
        assert user_record_after is None, f"用户 ID {user_id_to_delete} 在删除后仍然存在。"

        # 验证关联的 prompts 已被级联删除
        # cursor.execute(f"SELECT * FROM `{prompt_table}` WHERE user_id = %s", (user_id_to_delete,))
        # prompts_after = cursor.fetchall()
        # assert len(prompts_after) == 0, f"用户 ID {user_id_to_delete} 的关联 prompts 在删除后仍然存在。"
        # 更精确的验证：之前存在的 prompt id 现在应该查不到了
        if prompt_ids_before:
            placeholders = ', '.join(['%s'] * len(prompt_ids_before))
            cursor.execute(f"SELECT * FROM `{prompt_table}` WHERE id IN ({placeholders})", tuple(prompt_ids_before))
            prompts_after_specific = cursor.fetchall()
            assert len(prompts_after_specific) == 0, f"之前存在的 prompts (IDs: {prompt_ids_before}) 在用户删除后仍然存在。"

        # 验证关联的 api_tokens 已被级联删除
        # cursor.execute(f"SELECT * FROM `{api_token_table}` WHERE user_id = %s", (user_id_to_delete,))
        # tokens_after = cursor.fetchall()
        # assert len(tokens_after) == 0, f"用户 ID {user_id_to_delete} 的关联 api_tokens 在删除后仍然存在。"
        if token_ids_before:
            placeholders = ', '.join(['%s'] * len(token_ids_before))
            cursor.execute(f"SELECT * FROM `{api_token_table}` WHERE id IN ({placeholders})", tuple(token_ids_before))
            tokens_after_specific = cursor.fetchall()
            assert len(tokens_after_specific) == 0, f"之前存在的 api_tokens (IDs: {token_ids_before}) 在用户删除后仍然存在。"

def test_delete_record_invalid_table_name(client, db_setup_for_delete_tests):
    """测试 5.5: 删除时提供无效的表名。"""
    response = client.post('/delete_record', json={
        'table_name': 'non_existent_table',
        'primary_key': 'id',
        'primary_value': 1
    })

    assert response.status_code == 500 # 预期数据库层面错误导致 500
    response_data = response.get_json()
    assert 'error' in response_data
    # 具体的错误信息可能包含 "Table ... doesn't exist" 或类似的数据库错误代码1146
    assert "1146" in response_data['error'].lower() or "doesn't exist" in response_data['error'].lower()

def test_delete_record_missing_parameters(client, db_setup_for_delete_tests):
    """测试 5.6: 删除时缺少必要参数 (table_name, primary_key, primary_value)。"""
    base_payload = {
        'table_name': 'users',
        'primary_key': 'id',
        'primary_value': 2
    }

    test_cases = [
        {**base_payload, 'table_name': ''},      # 空 table_name
        {**base_payload, 'primary_key': ''},     # 空 primary_key
        {**base_payload, 'primary_value': None},  # primary_value 为 None (会被 json.dumps 转为 null)
        {'table_name': 'users', 'primary_key': 'id'}, # 缺少 primary_value
        {'table_name': 'users', 'primary_value': 1}, # 缺少 primary_key
        {'primary_key': 'id', 'primary_value': 1}    # 缺少 table_name
    ]

    for i, payload in enumerate(test_cases):
        response = client.post('/delete_record', json=payload)
        # print(f"Test case {i+1} payload: {payload}, Response: {response.get_data(as_text=True)}") # Debugging line
        assert response.status_code == 400, f"Test case {i+1} with payload {payload} did not return 400"
        response_data = response.get_json()
        assert 'error' in response_data
        assert response_data['error'] == "table_name, primary_key, and primary_value are required", \
               f"Test case {i+1} with payload {payload} returned wrong error message: {response_data['error']}"


"""
回顾 /delete_record 端点测试过程中遇到的主要问题及解决:

1. 模块导入问题 (ModuleNotFoundError: No module named 'app' / Unable to import 'database_utils')
   - 问题: 在 tests/ 子目录中运行测试时,Python 无法找到位于项目根目录的 app.py 和相关工具模块
   - 解决: 在测试文件的开头,动态地将项目根目录添加到 sys.path
     ```python
     # import sys
     # import os
     # project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
     # if project_root not in sys.path:
     #     sys.path.insert(0, project_root)
     ```
   - 后续发现: database_utils.py 并不存在,相关数据库函数(如 get_db_connection)直接从 app.py 导入

2. 数据库连接上下文管理器使用 (Generator 'generator' has no 'cursor' member)
   - 问题: get_db_connection 在 app.py 中使用了 @contextmanager 装饰器,直接调用返回的是生成器,而非连接对象
   - 解决: 使用 with get_db_connection() as conn: 语句来正确获取和管理数据库连接

3. 游标类型与数据访问 (KeyError: 0 / Unexpected keyword argument 'dictionary')
   - 问题1 (KeyError): app.py 中的 get_db_connection 设置了 cursorclass=pymysql.cursors.DictCursor,导致 fetchall() 返回字典列表。在 get_table_columns 中使用 row[0] 访问列名出错
   - 解决1: 修改为 row['Field'] 来访问字典键
   - 问题2 (Unexpected keyword argument): 由于已设置 DictCursor,在测试代码中调用 conn.cursor(dictionary=True) 是多余且错误的
   - 解决2: 修改为 conn.cursor()

4. 测试数据与测试目标不匹配 (AssertionError: 记录 ID 1 在删除前未在表 users 中找到)
   - 问题: 测试用例硬编码了要删除的记录 ID (例如 ID=1),但实际加载的 users.csv 中可能不存在该 ID
   - 解决: 通过调试打印确认 fixture 加载的数据,并修改测试用例以使用实际存在的记录 ID (例如 ID=2) 作为目标,或确保测试 CSV 文件包含目标 ID

5. API 请求体参数不匹配 (AssertionError: assert 400 == 200)
   - 问题: 测试用例向 /delete_record 发送的 JSON payload 字段名(如 record_id)与 API 端点期望的字段名(primary_key, primary_value)不符
   - 解决: 检查 API 端点代码,修改测试用例中的 payload 以匹配 API 的实际参数需求,并相应调整对成功响应消息的断言

6. 对 API 端点能力的理解 (关于测试用例 5.3 - 删除多条记录)
   - 初步理解: 认为 /delete_record 不支持通过 conditions 删除多条记录
   - 澄清与调整: 确认 /delete_record 虽然主要设计为基于主键删除,但通过将其 primary_key 参数指定为共享字段(如 user_id),可以实现删除所有匹配该字段值的记录,从而满足了特定场景下的"批量"删除需求。测试用例据此调整并成功实现
"""