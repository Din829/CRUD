import sys
import os
import pytest
import csv
from datetime import datetime

# 将项目根目录添加到 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import app as flask_app, get_db_connection

# 定义测试数据的相对路径
CSV_FILES_DIR = os.path.join(os.path.dirname(__file__), '')
USERS_CSV = os.path.join(CSV_FILES_DIR, 'users.csv')
PROMPTS_CSV = os.path.join(CSV_FILES_DIR, 'prompts.csv')
API_TOKENS_CSV = os.path.join(CSV_FILES_DIR, 'api_tokens.csv')

def get_table_columns_for_batch(conn, table_name):
    """获取表的列名，用于批量操作测试。"""
    cursor = conn.cursor()
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`") # Ensure backticks for table names
    columns = [row['Field'] for row in cursor.fetchall()]
    cleaned_columns = [col.lstrip('\ufeff').lstrip('﻿') for col in columns]
    return cleaned_columns

def load_csv_to_db_for_batch(conn, csv_path, table_name):
    """将 CSV 文件数据加载到数据库表中，用于批量操作测试。"""
    if not os.path.exists(csv_path):
        print(f"CSV file not found: {csv_path}")
        return

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        # Clean fieldnames from BOM characters
        fieldnames = [name.lstrip('\ufeff').lstrip('﻿') for name in reader.fieldnames if name]
        
        if not fieldnames:
            print(f"No fieldnames found in CSV: {csv_path}")
            return

        db_columns = get_table_columns_for_batch(conn, table_name)
        
        valid_fieldnames = [name for name in fieldnames if name in db_columns]
        
        if not valid_fieldnames:
            print(f"No valid fieldnames match DB columns for table {table_name} from CSV {csv_path}")
            return

        data_to_insert = []
        for row_number, row in enumerate(reader, 1):
            # Filter out rows that are entirely empty or just whitespace
            if not any(value and value.strip() for value in row.values()):
                # print(f"Skipping empty row {row_number} in {csv_path}")
                continue

            filtered_row = {}
            for key, value in row.items():
                cleaned_key = key.lstrip('\ufeff').lstrip('﻿')
                if cleaned_key in valid_fieldnames:
                    # Convert empty strings to None for appropriate SQL handling (especially for nullable fields)
                    filtered_row[cleaned_key] = None if value == '' else value
            
            if filtered_row: # Ensure there's something to insert after filtering
                 data_to_insert.append(filtered_row)

    if not data_to_insert:
        print(f"No data to insert for table {table_name} from {csv_path}")
        return

    columns_str = ', '.join([f"`{col}`" for col in valid_fieldnames])
    placeholders = ', '.join(['%s'] * len(valid_fieldnames))
    sql = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"

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
            # Optionally re-raise or handle more gracefully depending on test needs
            # For fixture setup, re-raising might be appropriate to fail the test early
            raise
    conn.commit()
    cursor.close()

@pytest.fixture(scope='function')
def client_for_batch():
    """提供 Flask 测试客户端。"""
    flask_app.config['TESTING'] = True
    # flask_app.config['PROPAGATE_EXCEPTIONS'] = True # Useful for debugging server-side errors
    with flask_app.test_client() as client:
        yield client

@pytest.fixture(scope='function')
def db_setup_for_batch_tests(client_for_batch): # Depends on the client fixture
    """在每个批量操作测试函数执行前清空并重新加载数据库。"""
    with get_db_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
            
            tables_to_clear = ['api_tokens', 'prompts', 'users']
            for table in tables_to_clear:
                cursor.execute(f"TRUNCATE TABLE `{table}`")
            conn.commit()
            
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
            conn.commit()

            # Load data in order of dependency
            load_csv_to_db_for_batch(conn, USERS_CSV, 'users')
            load_csv_to_db_for_batch(conn, PROMPTS_CSV, 'prompts')
            load_csv_to_db_for_batch(conn, API_TOKENS_CSV, 'api_tokens')
            
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
    yield client_for_batch # Yield the client for the test to use 

# 接下来是测试用例
def test_execute_batch_empty_operations_list(client_for_batch, db_setup_for_batch_tests):
    """测试 6.1: 空操作列表，验证响应。"""
    response = client_for_batch.post('/execute_batch_operations', json=[]) # 发送空列表

    assert response.status_code == 200 # 假设API优雅处理空列表并返回200
    response_data = response.get_json()
    # 响应格式依赖于API实现，这里假设它返回一个空结果列表和/或一个消息
    assert isinstance(response_data, dict) 
    assert response_data.get("message") == "No operations to perform." or response_data.get("results") == []

def test_execute_batch_only_inserts(client_for_batch, db_setup_for_batch_tests):
    """测试 6.2: 仅包含 insert 操作的批处理。"""
    operations = [
        {
            "operation": "insert",
            "table_name": "users",
            "values": {
                "username": "batch_user_1",
                "email": "batch1@example.com",
                "password": "pass123"
            }
        },
        {
            "operation": "insert",
            "table_name": "users",
            "values": {
                "username": "batch_user_2",
                "email": "batch2@example.com",
                "password": "pass456",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # 测试包含日期
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    ]

    response = client_for_batch.post('/execute_batch_operations', json=operations)
    assert response.status_code == 200
    response_data = response.get_json()
    assert isinstance(response_data, dict)
    results = response_data.get("results")
    assert isinstance(results, list) and len(results) == 2

    inserted_ids = []
    for i, result in enumerate(results):
        assert result.get("success") is True, f"Insert operation {i} failed: {result}" # Check 'success': true
        assert result.get("operation_index") == i # Verify operation index
        assert result.get("operation_type") == "insert" # Check 'operation_type'
        assert result.get("table_name") == "users"
        assert result.get("affected_rows") == 1 # For single insert, affected_rows should be 1
        last_id = result.get("last_insert_id") # Check 'last_insert_id'
        assert last_id is not None
        inserted_ids.append(last_id)

    # 验证数据库
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for i, op_id in enumerate(inserted_ids):
            cursor.execute("SELECT * FROM `users` WHERE id = %s", (op_id,))
            record = cursor.fetchone()
            assert record is not None
            assert record['username'] == operations[i]['values']['username']
            assert record['email'] == operations[i]['values']['email']

def test_execute_batch_only_updates(client_for_batch, db_setup_for_batch_tests):
    """测试 6.3: 仅包含 update 操作的批处理。"""
    # 假设用户 ID 2 (bob) 和 ID 4 (diana) 在 db_setup_for_batch_tests 后存在
    user_id_bob = 2
    user_id_diana = 4
    new_email_bob = "bob.updated.batch@example.com"
    new_username_diana = "diana_updated_batch"

    operations = [
        {
            "operation": "update",
            "table_name": "users",
            "set": {"email": new_email_bob},
            "where": {"id": user_id_bob}
        },
        {
            "operation": "update",
            "table_name": "users",
            "set": {"username": new_username_diana, "email": "diana.batch.updated@example.com"},
            "where": {"id": user_id_diana}
        },
        {
            "operation": "update", # 更新一个不存在的记录
            "table_name": "users",
            "set": {"username": "no_such_user_updated"},
            "where": {"id": 99998} # 不存在的ID
        },
        {
            "operation": "update", # 测试 where id IN [] (空列表)
            "table_name": "users",
            "set": {"email": "update_for_empty_in@example.com"},
            "where": {"id": {"IN": []}} # 假设API处理这种情况为0行受影响
        }
    ]

    response = client_for_batch.post('/execute_batch_operations', json=operations)
    assert response.status_code == 200
    response_data = response.get_json()
    assert isinstance(response_data, dict)
    results = response_data.get("results")
    assert isinstance(results, list) and len(results) == 4 # Expect 4 operations results

    for i, result in enumerate(results):
        assert result.get("success") is True, f"Update operation {i} failed: {result}"
        assert result.get("operation_index") == i
        assert result.get("operation_type") == "update"
        assert result.get("table_name") == "users"
        assert result.get("last_insert_id") is None # Should be None for updates

        if i == 0: # First operation: update bob
            assert result.get("affected_rows") == 1
        elif i == 1: # Second operation: update diana (ID 4)
            assert result.get("affected_rows") == 1 # This was missing in the previous logic
        elif i == 2: # Third operation: update non_existent_user
            assert result.get("affected_rows") == 0 # No rows updated
        elif i == 3: # Fourth operation: update with empty IN clause (should affect 0)
            assert result.get("affected_rows") == 0

    # 验证数据库
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM `users` WHERE id = %s", (user_id_bob,))
        assert cursor.fetchone()['email'] == new_email_bob
        cursor.execute("SELECT username, email FROM `users` WHERE id = %s", (user_id_diana,))
        diana_record = cursor.fetchone()
        assert diana_record['username'] == new_username_diana
        assert diana_record['email'] == "diana.batch.updated@example.com"

def test_execute_batch_only_deletes(client_for_batch, db_setup_for_batch_tests):
    """测试 6.4: 仅包含 delete 操作的批处理。"""
    # 假设用户 ID 6 (fiona) 和 ID 9 (ian) 在 setup 后存在
    user_id_fiona = 6
    user_id_ian = 9

    operations = [
        {
            "operation": "delete",
            "table_name": "users",
            "where": {"id": user_id_fiona}
        },
        {
            "operation": "delete",
            "table_name": "users",
            "where": {"id": user_id_ian}
        },
        {
            "operation": "delete", # 删除一个不存在的记录
            "table_name": "users",
            "where": {"id": 99997} # 不存在的ID
        }
    ]

    response = client_for_batch.post('/execute_batch_operations', json=operations)
    assert response.status_code == 200
    response_data = response.get_json()
    assert isinstance(response_data, dict)
    results = response_data.get("results")
    assert isinstance(results, list) and len(results) == 3

    for i, result in enumerate(results):
        assert result.get("success") is True, f"Delete operation {i} failed: {result}"
        assert result.get("operation_index") == i
        assert result.get("operation_type") == "delete"
        assert result.get("table_name") == "users"
        assert result.get("last_insert_id") is None

        if i == 0:  # First operation: delete fiona (ID 6)
            assert result.get("affected_rows") == 1
        elif i == 1:  # Second operation: delete ian (ID 9)
            assert result.get("affected_rows") == 1
        elif i == 2:  # Third operation: delete non-existent_user (ID 99997)
            assert result.get("affected_rows") == 0

    # 验证数据库
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM `users` WHERE id = %s", (user_id_fiona,))
        assert cursor.fetchone() is None
        cursor.execute("SELECT * FROM `users` WHERE id = %s", (user_id_ian,))
        assert cursor.fetchone() is None 

def test_execute_batch_mixed_operations(client_for_batch, db_setup_for_batch_tests):
    """测试 6.5: 混合 insert, update, delete 操作的批处理。"""
    # 初始数据: user ID 2 (bob), user ID 4 (diana) 从 CSV 加载
    user_id_bob = 2
    user_id_to_delete = 4 # 改为存在的用户 ID，例如 Diana (ID 4)
    new_user_username_for_insert = "mixed_insert_user"
    new_user_email_for_insert = "newmixed@example.com"
    updated_bob_username = "bob_mixed_updated"

    operations = [
        {
            "operation": "insert",
            "table_name": "users",
            "values": {
                "username": new_user_username_for_insert,
                "email": new_user_email_for_insert,
                "password": "mixedpass"
            }
        },
        {
            "operation": "update",
            "table_name": "users",
            "set": {"username": updated_bob_username},
            "where": {"id": user_id_bob}
        },
        {
            "operation": "delete",
            "table_name": "users",
            "where": {"id": user_id_to_delete} 
        }
    ]

    response = client_for_batch.post('/execute_batch_operations', json=operations)
    assert response.status_code == 200
    response_data = response.get_json()
    assert isinstance(response_data, dict)
    assert response_data.get("message") == "Batch operations executed successfully."
    results = response_data.get("results")
    assert isinstance(results, list) and len(results) == 3

    # 验证 Insert 操作 (index 0)
    insert_result = results[0]
    assert insert_result.get("success") is True
    assert insert_result.get("operation_index") == 0
    assert insert_result.get("operation_type") == "insert"
    assert insert_result.get("table_name") == "users"
    assert insert_result.get("affected_rows") == 1
    inserted_user_id = insert_result.get("last_insert_id")
    assert inserted_user_id is not None

    # 验证 Update 操作 (index 1)
    update_result = results[1]
    assert update_result.get("success") is True
    assert update_result.get("operation_index") == 1
    assert update_result.get("operation_type") == "update"
    assert update_result.get("table_name") == "users"
    assert update_result.get("affected_rows") == 1
    assert update_result.get("last_insert_id") is None

    # 验证 Delete 操作 (index 2)
    delete_result = results[2]
    assert delete_result.get("success") is True
    assert delete_result.get("operation_index") == 2
    assert delete_result.get("operation_type") == "delete"
    assert delete_result.get("table_name") == "users"
    assert delete_result.get("affected_rows") == 1 # ID 4 应该存在并被删除
    assert delete_result.get("last_insert_id") is None

    # 验证数据库状态
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 1. 验证新用户已插入
        cursor.execute("SELECT * FROM `users` WHERE id = %s", (inserted_user_id,))
        new_user_record = cursor.fetchone()
        assert new_user_record is not None
        assert new_user_record['username'] == new_user_username_for_insert
        assert new_user_record['email'] == new_user_email_for_insert

        # 2. 验证 bob (ID 2) 已更新
        cursor.execute("SELECT username FROM `users` WHERE id = %s", (user_id_bob,))
        bob_record = cursor.fetchone()
        assert bob_record is not None
        assert bob_record['username'] == updated_bob_username

        # 3. 验证被删除的用户 (ID 4) 已不存在
        cursor.execute("SELECT * FROM `users` WHERE id = %s", (user_id_to_delete,))
        assert cursor.fetchone() is None
        
        cursor.close() 

def test_batch_dependency_insert_to_insert(client_for_batch, db_setup_for_batch_tests):
    """测试 6.6.1: 后续 insert 操作依赖前序 insert 返回的 ID (通过 return_affected)。"""
    new_user_username = "dependent_user"
    new_user_email = "dependent_user@example.com"
    prompt_title = "My First Prompt for Dependent User"

    operations = [
        {
            "operation": "insert",
            "table_name": "users",
            "values": {
                "username": new_user_username,
                "email": new_user_email,
                "password": "depPass123"
            },
            "return_affected": ["id"] # 关键: 返回新用户的ID
        },
        {
            "operation": "insert",
            "table_name": "prompts",
            "depends_on_index": 0, # 依赖前一个操作
            "values": {
                "user_id": "{{previous_result[0].id}}", # 使用占位符引用ID
                "title": prompt_title,
                "content": "This prompt depends on the user inserted in the previous step.",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    ]

    response = client_for_batch.post('/execute_batch_operations', json=operations)
    assert response.status_code == 200
    response_data = response.get_json()
    assert isinstance(response_data, dict), f"Unexpected response type: {response_data}"
    assert response_data.get("message") == "Batch operations executed successfully."
    results = response_data.get("results")
    assert isinstance(results, list) and len(results) == 2, f"Expected 2 results, got {len(results) if results else 'None'}"

    # 验证第一个 insert (users)
    user_insert_result = results[0]
    assert user_insert_result.get("success") is True
    assert user_insert_result.get("operation_index") == 0
    assert user_insert_result.get("operation_type") == "insert"
    assert user_insert_result.get("table_name") == "users"
    assert user_insert_result.get("affected_rows") == 1
    inserted_user_id = user_insert_result.get("last_insert_id")
    assert inserted_user_id is not None

    # 验证第二个 insert (prompts)
    prompt_insert_result = results[1]
    assert prompt_insert_result.get("success") is True, f"Prompt insert failed: {prompt_insert_result}"
    assert prompt_insert_result.get("operation_index") == 1
    assert prompt_insert_result.get("operation_type") == "insert"
    assert prompt_insert_result.get("table_name") == "prompts"
    assert prompt_insert_result.get("affected_rows") == 1
    inserted_prompt_id = prompt_insert_result.get("last_insert_id")
    assert inserted_prompt_id is not None

    # 验证数据库状态
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 1. 验证用户已插入
        cursor.execute("SELECT id, username, email FROM `users` WHERE id = %s", (inserted_user_id,))
        user_record = cursor.fetchone()
        assert user_record is not None
        assert user_record['username'] == new_user_username
        assert user_record['email'] == new_user_email

        # 2. 验证 prompt 已插入并关联了正确的 user_id
        cursor.execute("SELECT id, user_id, title FROM `prompts` WHERE id = %s", (inserted_prompt_id,))
        prompt_record = cursor.fetchone()
        assert prompt_record is not None
        assert prompt_record['user_id'] == inserted_user_id # 关键: 验证依赖关系
        assert prompt_record['title'] == prompt_title
        
        cursor.close() 

def test_batch_dependency_update_to_insert_single_row(client_for_batch, db_setup_for_batch_tests):
    """测试 6.6.2: insert 依赖 update 返回的单行 return_affected 数据。"""
    user_id_to_update = 2 # 假设用户 bob (ID 2) 存在
    updated_email = "bob.updated.for.dependency@example.com"
    
    operations = [
        {
            "operation": "update",
            "table_name": "users",
            "set": {"email": updated_email, "username": "bob_dep_updated"},
            "where": {"id": user_id_to_update},
            "return_affected": ["id", "username", "email"] # 返回更新后的字段
        },
        {
            "operation": "insert",
            "table_name": "prompts",
            "depends_on_index": 0,
            "values": {
                "user_id": "{{previous_result[0].id}}", 
                "title": "Prompt for {{previous_result[0].username}}",
                "content": "Data from updated user: Email {{previous_result[0].email}}",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    ]

    response = client_for_batch.post('/execute_batch_operations', json=operations)
    assert response.status_code == 200
    response_data = response.get_json()
    assert isinstance(response_data, dict), f"Unexpected response type: {response_data}"
    assert response_data.get("message") == "Batch operations executed successfully."
    results = response_data.get("results")
    assert isinstance(results, list) and len(results) == 2, f"Expected 2 results, got {len(results) if results else 'None'}"

    # 验证第一个 update (users)
    update_result = results[0]
    assert update_result.get("success") is True
    assert update_result.get("operation_index") == 0
    assert update_result.get("operation_type") == "update"
    assert update_result.get("table_name") == "users"
    assert update_result.get("affected_rows") == 1

    # 验证第二个 insert (prompts)
    prompt_insert_result = results[1]
    assert prompt_insert_result.get("success") is True, f"Prompt insert failed: {prompt_insert_result}"
    assert prompt_insert_result.get("operation_index") == 1
    assert prompt_insert_result.get("operation_type") == "insert"
    assert prompt_insert_result.get("table_name") == "prompts"
    assert prompt_insert_result.get("affected_rows") == 1
    inserted_prompt_id = prompt_insert_result.get("last_insert_id")
    assert inserted_prompt_id is not None

    # 验证数据库状态
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 1. 验证用户已更新
        cursor.execute("SELECT id, username, email FROM `users` WHERE id = %s", (user_id_to_update,))
        user_record = cursor.fetchone()
        assert user_record is not None
        assert user_record['username'] == "bob_dep_updated"
        assert user_record['email'] == updated_email

        # 2. 验证 prompt 已插入并使用了更新后的用户数据
        cursor.execute("SELECT id, user_id, title, content FROM `prompts` WHERE id = %s", (inserted_prompt_id,))
        prompt_record = cursor.fetchone()
        assert prompt_record is not None
        assert prompt_record['user_id'] == user_id_to_update
        assert prompt_record['title'] == f"Prompt for {user_record['username']}" 
        assert prompt_record['content'] == f"Data from updated user: Email {user_record['email']}"
        
        cursor.close() 

def test_batch_dependency_update_to_insert_multiple_rows_expansion(client_for_batch, db_setup_for_batch_tests):
    """测试 6.6.3: insert 依赖 update 返回的多行 return_affected 数据，并验证操作展开。"""
    user_ids_to_update = [2, 4] # bob (ID 2) 和 diana (ID 4)
    original_usernames = {}
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for user_id in user_ids_to_update:
            cursor.execute("SELECT username FROM `users` WHERE id = %s", (user_id,))
            record = cursor.fetchone()
            assert record is not None, f"Test setup error: User ID {user_id} not found."
            original_usernames[user_id] = record['username']
        cursor.close()

    updated_username_suffix = "_expanded"

    operations = [
        {
            "operation": "update",
            "table_name": "users",
            "set": {"username": f"CONCAT(username, '{updated_username_suffix}')"},
            "where": {"id": {"IN": user_ids_to_update}},
            "return_affected": ["id", "username"] 
        },
        {
            "operation": "insert",
            "table_name": "prompts",
            "depends_on_index": 0, 
            "values": {
                "user_id": "{{previous_result[0].id}}",
                "title": "Auto-prompt for {{previous_result[0].username}}",
                "content": "This prompt was auto-generated after user update.",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    ]

    response = client_for_batch.post('/execute_batch_operations', json=operations)
    assert response.status_code == 200
    response_data = response.get_json()
    assert isinstance(response_data, dict), f"Unexpected response type: {response_data}"
    assert response_data.get("message") == "Batch operations executed successfully."
    results = response_data.get("results")
    
    # 预期结果数量: 1个update操作 + len(user_ids_to_update)个展开的insert操作
    expected_total_results = 1 + len(user_ids_to_update)
    assert isinstance(results, list) and len(results) == expected_total_results, f"Expected {expected_total_results} results (1 update + {len(user_ids_to_update)} expanded inserts), got {len(results) if results else 'None'}. Results: {results}"

    update_op_result = results[0]
    assert update_op_result.get("success") is True
    assert update_op_result.get("operation_index") == 0 # update 操作是原始操作列表中的第0个
    assert update_op_result.get("expansion_index") is None # update 操作本身未展开
    assert update_op_result.get("operation_type") == "update"
    assert update_op_result.get("table_name") == "users"
    assert update_op_result.get("affected_rows") == len(user_ids_to_update)
    # 从 update 操作的返回结果中提取更新后的用户信息
    affected_data_from_update = update_op_result.get("affected_data", [])
    assert len(affected_data_from_update) == len(user_ids_to_update), "Update operation did not return affected_data for all updated users."
    
    expanded_user_info_map = {
        item['id']: item['username'] for item in affected_data_from_update
    }

    # 筛选出属于原始操作1 (insert) 的展开结果
    expanded_insert_results = sorted(
        [res for res in results if res.get("operation_index") == 1 and res.get("expansion_index") is not None],
        key=lambda x: x.get("expansion_index")
    )
    assert len(expanded_insert_results) == len(user_ids_to_update), f"Number of expanded inserts ({len(expanded_insert_results)}) does not match number of updated users ({len(user_ids_to_update)})."

    # 验证每个展开的 insert 操作
    for i, insert_res in enumerate(expanded_insert_results):
        assert insert_res.get("success") is True, f"Expanded insert {i} failed: {insert_res}"
        assert insert_res.get("expansion_index") == i 
        assert insert_res.get("operation_type") == "insert"
        assert insert_res.get("table_name") == "prompts"
        assert insert_res.get("affected_rows") == 1
        current_prompt_id = insert_res.get("last_insert_id")
        assert current_prompt_id is not None

        # 验证数据库状态
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, title FROM `prompts` WHERE id = %s", (current_prompt_id,))
            prompt_record = cursor.fetchone()
            assert prompt_record is not None, f"Prompt ID {current_prompt_id} not found."
            # 验证 prompt 是否关联了正确的 user_id 并且 title 是否使用了更新后的 username
            prompt_user_id = prompt_record['user_id']
            assert prompt_user_id in expanded_user_info_map, f"Prompt {current_prompt_id} linked to unexpected user_id {prompt_user_id}. Expected one of {list(expanded_user_info_map.keys())}"
            
            expected_username_for_title = expanded_user_info_map[prompt_user_id]
            expected_title = f"Auto-prompt for {expected_username_for_title}"
            assert prompt_record['title'] == expected_title, f"Prompt title mismatch for prompt ID {current_prompt_id}. Expected '{expected_title}', got '{prompt_record['title']}'."
            cursor.close() 

def test_batch_error_handling_rollback_unique_constraint(client_for_batch, db_setup_for_batch_tests):
    """测试 6.7.1 & 6.7.2: 唯一约束冲突导致事务回滚及错误报告。
    - 验证批处理中某个操作失败时，整个事务是否回滚。
    - 验证返回的错误信息是否能准确定位到失败的操作索引和原因。
    """
    initial_user_email_to_conflict = "error_user_tx@example.com" # 这个 email 将被用作冲突点

    operations = [
        {
            "operation": "insert",
            "table_name": "users",
            "values": {
                "username": "good_user_before_error",
                "email": initial_user_email_to_conflict, # 第一次插入这个 email
                "password": "pass123"
            }
        },
        {
            "operation": "insert",
            "table_name": "users",
            "values": {
                "username": "bad_user_causes_error",
                "email": initial_user_email_to_conflict, # 第二次插入相同的 email，导致冲突
                "password": "pass456"
            }
        },
        {
            "operation": "insert",
            "table_name": "users",
            "values": {
                "username": "good_user_after_error_not_inserted",
                "email": "another_good_email_tx@example.com",
                "password": "pass789"
            }
        }
    ]

    response = client_for_batch.post('/execute_batch_operations', json=operations)

    # 1. 验证响应状态码和顶层错误信息
    assert response.status_code == 409 # MySQL 1062 错误 (Duplicate entry) 应该返回 409 Conflict
    response_data = response.get_json()
    assert isinstance(response_data, dict), "Response should be a dict"
    assert response_data.get("error") == "Unique constraint violation during batch operation."
    
    # 2. 验证详细错误信息 (6.7.2)
    error_detail = response_data.get("detail")
    assert isinstance(error_detail, dict), "Error detail should be a dict"
    assert error_detail.get("type") == "IntegrityError.DuplicateEntry"
    assert error_detail.get("failed_operation_index") == 1 # 第二个操作 (index 1) 失败
    assert error_detail.get("table_name") == "users"
    assert error_detail.get("conflicting_value") == initial_user_email_to_conflict
    assert "key_name" in error_detail # 例如 users.email_UNIQUE 或类似的键名

    results_array = response_data.get("results")
    assert isinstance(results_array, list), "Results array should be present, even on error"
    # 验证第一个操作的结果 (如果 API 返回了它的话，它应该是成功的，但会被回滚)
    if len(results_array) > 0:
        op0_result = results_array[0]
        assert op0_result.get("success") is True # API层面可能认为它成功了，但DB会回滚
        assert op0_result.get("operation_index") == 0
        assert op0_result.get("operation_type") == "insert"

    # 3. 验证数据库状态以确认回滚 (6.7.1)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 第一个用户 "good_user_before_error" 不应该存在 (已回滚)
        cursor.execute("SELECT * FROM `users` WHERE email = %s", (initial_user_email_to_conflict,))
        assert cursor.fetchone() is None, f"User with email {initial_user_email_to_conflict} should have been rolled back."

        # 尝试插入的第二个用户 "bad_user_causes_error" 不应该存在
        # (它的 email 与第一个相同，所以上面的检查也覆盖了它)

        # 第三个用户 "good_user_after_error_not_inserted" 不应该存在 (未执行)
        cursor.execute("SELECT * FROM `users` WHERE email = %s", ("another_good_email_tx@example.com",))
        assert cursor.fetchone() is None, "User 'good_user_after_error_not_inserted' should not have been inserted."
        
        cursor.close()

def test_batch_set_clause_sql_expressions(client_for_batch, db_setup_for_batch_tests):
    """测试 6.8: `set` 子句中的 SQL 表达式（如 `CONCAT()`, `NOW()`）是否正确执行。"""
    user_id_to_update = 2 # 假设用户 bob (ID 2) 存在
    original_username = "bob"
    username_suffix_to_concat = "_expr_updated"
    expected_username_after_concat = original_username + username_suffix_to_concat

    operations = [
        {
            "operation": "update",
            "table_name": "users",
            "set": {
                "username": f"CONCAT(username, '{username_suffix_to_concat}')", # 使用 CONCAT
                "updated_at": "NOW()" # 使用 NOW()
            },
            "where": {"id": user_id_to_update}
        }
    ]

    response = client_for_batch.post('/execute_batch_operations', json=operations)
    assert response.status_code == 200
    response_data = response.get_json()
    assert isinstance(response_data, dict)
    results = response_data.get("results")
    assert isinstance(results, list) and len(results) == 1

    update_result = results[0]
    assert update_result.get("success") is True
    assert update_result.get("operation_index") == 0
    assert update_result.get("operation_type") == "update"
    assert update_result.get("table_name") == "users"
    assert update_result.get("affected_rows") == 1

    # 验证数据库状态
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, updated_at FROM `users` WHERE id = %s", (user_id_to_update,))
        record = cursor.fetchone()
        assert record is not None
        assert record['username'] == expected_username_after_concat, (
               f"Username did not update correctly with CONCAT. Expected '{expected_username_after_concat}', got '{record['username']}'."
        )
        
        # 验证 updated_at 是否被更新 (大致检查，因为它会是当前时间)
        # 首先确保它不是初始的CSV值或一个非常旧的时间戳
        initial_updated_at_str = "2024-01-01 00:00:00" # 一个明显早于NOW()的时间
        try:
            initial_updated_at_dt = datetime.strptime(initial_updated_at_str, "%Y-%m-%d %H:%M:%S")
            assert record['updated_at'] > initial_updated_at_dt, (
                   f"updated_at ('{record['updated_at']}') was not updated by NOW() or is older than expected."
            )
        except TypeError: # record['updated_at'] 可能已经是 datetime 对象
            if isinstance(record['updated_at'], datetime):
                assert record['updated_at'] > datetime.strptime(initial_updated_at_str, "%Y-%m-%d %H:%M:%S"), (
                    f"updated_at ('{record['updated_at']}') was not updated by NOW() or is older than expected (datetime comparison)."
                )
            else:
                raise AssertionError(f"record['updated_at'] is of unexpected type: {type(record['updated_at'])}")

        # 还可以检查它是否非常接近当前时间，但要注意时区和执行延迟
        now_utc = datetime.utcnow()
        time_difference_seconds = abs((record['updated_at'].replace(tzinfo=None) - now_utc).total_seconds())
        assert time_difference_seconds < 10, (
            f"updated_at difference from now_utc is {time_difference_seconds}s, which might be too large."
        )
        
        cursor.close()

def test_batch_where_clause_operators(client_for_batch, db_setup_for_batch_tests):
    """测试 6.9: `where` 子句中多种条件操作符的正确性。"""
    # 为测试准备一些特定数据，或依赖 fixture 中的数据
    # 例如，我们可以确保 fixture 加载的用户 ID 包含 1, 2, 3, 4, 5, 6 等用于测试

    user_id_bob = 2     # username 'bob', email 'bob@example.com'
    user_id_carol = 3   # username 'carol', email 'carol@example.com'
    user_id_diana = 4   # username 'diana', email 'diana@example.com'
    user_id_edward = 5  # username 'edward', email 'edward@example.com'
    user_id_fiona = 6   # username 'fiona', email 'fiona@example.com'

    # 先查询数据库，获取满足特定条件的初始数量，以便准确断言 affected_rows
    initial_users_gt_3_count = 0
    initial_users_lt_4_non_target_email_count = 0 # 用于 Op 2
    initial_users_between_5_6_count = 0 # 用于 Op 3
    initial_user_edward_exists = False # 用于 Op 4

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM `users` WHERE id > %s", (3,))
        initial_users_gt_3_count = cursor.fetchone()['count']
        
        # 为 Op 2 的 NOT LIKE 和 < 准备计数
        # 假设 bob (ID 2) 和 carol (ID 3) 的 email 不是 'updated.by.like_id_...'
        # 并且它们的 ID < 4
        cursor.execute("SELECT COUNT(*) as count FROM `users` WHERE id < %s AND email NOT LIKE %s", (4, 'updated.by.like_id_%'))
        initial_users_lt_4_non_target_email_count = cursor.fetchone()['count']

        # 为 Op 3 的 BETWEEN 准备计数
        cursor.execute("SELECT COUNT(*) as count FROM `users` WHERE id BETWEEN %s AND %s", (5, 6))
        initial_users_between_5_6_count = cursor.fetchone()['count']
        
        # 为 Op 4 的 IN [user_id_edward] 准备计数
        user_id_edward = 5 # 明确一下 edward 的 ID
        cursor.execute("SELECT COUNT(*) as count FROM `users` WHERE id = %s", (user_id_edward,))
        initial_user_edward_exists = cursor.fetchone()['count'] > 0
        cursor.close()

    operations = [
        {
            "operation": "update", # 1. 测试 '>' 操作符
            "table_name": "users",
            "set": {"username": "CONCAT('user_gt_3_id_', id)"}, # 使用 CONCAT 和 id 确保唯一性
            "where": {"id": {">": 3}} # 应该影响 ID 4, 5, 6 (diana, edward, fiona)
        },
        {
            "operation": "update", # 2. 测试 'LIKE' 操作符
            "table_name": "users",
            "set": {"email": "CONCAT('updated.by.like_id_', id, '@example.com')"}, # 使用 CONCAT 和 id 确保 email 唯一性
            "where": {"username": {"LIKE": "user_gt_3_id_%"}} # 基于上一个操作的结果调整 LIKE 模式
        },
        {
            "operation": "delete", # 3. 测试 'NOT IN' 操作符
            "table_name": "users",
            # 删除所有 email 不是 'updated.by.like_id_X@example.com' 格式 (即原始 email) 且 ID < 4 的用户
            # 即删除 bob (ID 2), carol (ID 3)
            "where": {
                # 假设 bob@example.com 和 carol@example.com 不会匹配下面的模式
                "email": {"NOT LIKE": "updated.by.like_id_%@example.com"}, 
                "id": {"<": 4}
            }
        },
        {
            "operation": "update", # 4. 测试 'BETWEEN' 操作符 (假设 ID 5,6 仍然是 user_gt_3)
            "table_name": "users",
            "set": {"password": "pass_between_5_6"},
            "where": {"id": {"BETWEEN": [5, 6]}} # 应该影响 ID 5, 6
        },
        {
            "operation": "delete", # 5. 测试 'IN' 再次确认 (删除 ID 5)
            "table_name": "users",
            "where": {"id": {"IN": [user_id_edward]}}
        }
    ]

    response = client_for_batch.post('/execute_batch_operations', json=operations)
    assert response.status_code == 200
    response_data = response.get_json()
    assert isinstance(response_data, dict)
    results = response_data.get("results")
    assert isinstance(results, list) and len(results) == len(operations)

    # 验证每个操作的 affected_rows
    # Op 0: update id > 3
    assert results[0].get("success") is True and results[0].get("affected_rows") == initial_users_gt_3_count
    # Op 1: update username LIKE 'user_gt_3_id_%' (should be same count as Op 0)
    assert results[1].get("success") is True and results[1].get("affected_rows") == initial_users_gt_3_count
    # Op 2: delete email NOT LIKE 'updated.by.like_id_%' AND id < 4
    assert results[2].get("success") is True and results[2].get("affected_rows") == initial_users_lt_4_non_target_email_count
    # Op 3: update id BETWEEN 5 AND 6
    assert results[3].get("success") is True and results[3].get("affected_rows") == initial_users_between_5_6_count
    # Op 4: delete id IN [user_id_edward]
    expected_op4_affected = 1 if initial_user_edward_exists else 0
    # 考虑到Op3可能已经修改了user_id_edward(5)的password，但Op4是删除它，所以如果存在就应该被删除
    # 但是，如果Op3更新了记录，而Op4尝试删除一个不再存在的记录（因为前面的操作可能已经删除了它），这里需要小心。
    # 在这个串行流程中，ID 5 在 Op3 中被更新，然后在 Op4 中被删除。所以期望是1（如果它开始时存在）
    assert results[4].get("success") is True and results[4].get("affected_rows") == expected_op4_affected

    # 验证数据库最终状态
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 检查 ID 2 (bob) 和 ID 3 (carol) 是否已被删除 (by Op 2)
        cursor.execute("SELECT COUNT(*) as count FROM `users` WHERE id IN (%s, %s)", (user_id_bob, user_id_carol))
        assert cursor.fetchone()['count'] == 0, "Users bob (ID 2) and carol (ID 3) should have been deleted."

        # 检查 ID 4 (diana) 的状态： username='user_gt_3_id_4', email='updated.by.like_id_4@example.com'
        cursor.execute("SELECT username, email FROM `users` WHERE id = %s", (user_id_diana,))
        diana_record = cursor.fetchone()
        assert diana_record is not None, "User diana (ID 4) should exist."
        assert diana_record['username'] == "user_gt_3_id_4"
        assert diana_record['email'] == "updated.by.like_id_4@example.com"

        # 检查 ID 5 (edward) 是否已被删除 (by Op 4)
        cursor.execute("SELECT COUNT(*) as count FROM `users` WHERE id = %s", (user_id_edward,))
        assert cursor.fetchone()['count'] == 0, "User edward (ID 5) should have been deleted."

        # 检查 ID 6 (fiona) 的状态： username='user_gt_3_id_6', email='updated.by.like_id_6@example.com', password='pass_between_5_6'
        cursor.execute("SELECT username, email, password FROM `users` WHERE id = %s", (user_id_fiona,))
        fiona_record = cursor.fetchone()
        assert fiona_record is not None, "User fiona (ID 6) should exist."
        assert fiona_record['username'] == "user_gt_3_id_6"
        assert fiona_record['email'] == "updated.by.like_id_6@example.com"
        assert fiona_record['password'] == "pass_between_5_6"

        cursor.close()

# === 总结：复合依赖与操作展开测试调试 (针对 6.6.x 系列) ===
#
# 1. 占位符替换 (Placeholder Replacement):
#    - 问题: `re.match` 仅从字符串开头匹配，无法处理 `field: "Text {{placeholder}}"` 这类场景。
#    - 解决: 改用 `re.sub` 进行全局替换。引入 `effective_depends_on_index_for_regex` 参数确保占位符
#            `{{previous_result[N].column}}` 中的 `N` 与操作声明的 `depends_on_index` 严格对应。
#
# 2. 操作展开 (Operation Expansion for Multi-Row Dependencies):
#    - 问题: 当一个操作依赖于前序操作返回的多行结果 (例如，一个 update 返回了多个被影响的行)，
#            后续操作需要为每一行依赖结果分别执行一次（即"展开"）。
#    - 解决:
#        - 在 `app.py` 的 `execute_batch_operations` 中，当 `base_dependent_result` 是列表时，
#          将其赋值给 `dependent_result_list`。
#        - 循环遍历 `dependent_result_list`，对每个依赖项，深拷贝当前操作并使用该依赖项替换占位符，
#          然后执行这个展开后的操作。
#
# 3. `return_affected` 数据在最终结果中的传递:
#    - 问题: 通过 `return_affected` 从数据库获取的数据（例如更新后的行），虽然在内部被用于后续占位符替换，
#            但并未包含在API返回给客户端的每个操作的最终结果对象中 (即 `step_result`)。
#    - 解决: 在 `app.py` 的 `_execute_single_op` 中，将获取到的 `_current_op_result_for_cache`
#            (即 `affected_data`) 也添加到返回的 `step_result` 字典中。
#
# 4. 测试中断言逻辑修正:
#    - 问题: 测试代码在断言时，可能错误地判断了哪个原始操作的 `operation_index` 应该关联展开的结果，
#            或者如何从API返回的 `results` 列表中正确筛选和验证这些展开的操作。
#    - 解决: 仔细核对测试场景，确保断言逻辑与API的实际展开行为和返回结构一致。例如，如果
#            操作 `B` (index 1) 依赖操作 `A` (index 0)，且 `A` 返回多行导致 `B` 展开，
#            那么展开后的结果应该具有 `operation_index: 1` 和递增的 `expansion_index`。
#
# 5. 动态断言 affected_rows (Dynamic Assertion of affected_rows):
#    - 问题: 在测试 `WHERE` 子句的多种操作符时 (`test_batch_where_clause_operators`)，
#            最初对 `affected_rows` 的期望值是基于对 `users.csv` 内容的假设（例如，`id > 3` 只影响几行）。
#            当 `users.csv` 包含更多数据时，实际影响的行数与硬编码的期望值不符，导致断言失败。
#    - 解决: 在执行API调用前，先通过数据库查询动态计算出每个操作的 `WHERE` 条件预期会影响的行数。
#            在断言 `affected_rows` 时使用这些动态获取的计数值。同时，数据库最终状态的验证也应
#            采用更鲁棒的方式，如查询 `COUNT(*)` 来确认记录是否存在，而不是依赖可能已过时的具体数据值。
#
# 这些调整确保了 `/execute_batch_operations` 端点能正确处理复杂的依赖关系和动态操作扩展，
# 特别是当一个操作依赖于前一个操作返回的多条记录时。 