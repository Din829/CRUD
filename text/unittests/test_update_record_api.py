import pytest
import json
import os
import sys
from datetime import datetime, timedelta
import csv
import pymysql # 确保导入，fixture 可能需要

# 将项目根目录添加到 sys.path 以便导入 app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, get_db_connection # 从项目的 app.py 导入 Flask app 和数据库连接函数

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['PROPAGATE_EXCEPTIONS'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(scope='function')
def db_setup_for_update_tests():
    """
    为更新操作的单元测试设置数据库到已知状态。
    清空相关表 (users, prompts, api_tokens) 并从 CSV 文件重新加载数据。
    与 db_setup_for_insert_tests 功能相同，但为 update 测试明确命名。
    """
    tables_to_reset = {
        'users': 'text/users.csv',
        'prompts': 'text/prompts.csv',
        'api_tokens': 'text/api_tokens.csv'
    }
    # 删除顺序考虑外键：api_tokens 和 prompts 依赖 users
    truncation_order = ['api_tokens', 'prompts', 'users']
    # 插入顺序考虑外键：users 先于 prompts 和 api_tokens
    insertion_order = ['users', 'prompts', 'api_tokens']

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
                for table_name in truncation_order:
                    app.logger.debug(f"为更新测试清空表 {table_name}...")
                    cursor.execute(f"TRUNCATE TABLE `{table_name}`")
                cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
                connection.commit()

                for table_name in insertion_order:
                    csv_file_path = tables_to_reset[table_name]
                    app.logger.debug(f"从 {csv_file_path} 为更新测试加载数据到 {table_name}...")
                    try:
                        with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
                            reader = csv.DictReader(csvfile)
                            if reader.fieldnames:
                                cleaned_fieldnames = [name.lstrip('\ufeff') for name in reader.fieldnames]
                                reader.fieldnames = cleaned_fieldnames
                            if not reader.fieldnames:
                                app.logger.warning(f"CSV 文件 {csv_file_path} 为空或没有表头。")
                                continue
                            
                            columns = [f"`{col}`" for col in reader.fieldnames]
                            placeholders = ['%s'] * len(columns)
                            insert_sql = f"INSERT INTO `{table_name}` ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                            
                            rows_to_insert = []
                            for row_dict in reader:
                                ordered_values = []
                                for field in reader.fieldnames:
                                    value = row_dict.get(field)
                                    # 基本的 None 和空字符串处理
                                    if value == '' or value is None:
                                        ordered_values.append(None)
                                    # 特定于表的 ID 类型转换 (如果CSV中ID是字符串)
                                    elif field == 'id' and table_name in ['users', 'prompts', 'api_tokens']:
                                        ordered_values.append(int(value) if value and value.strip() else None)
                                    elif field == 'user_id' and table_name in ['prompts', 'api_tokens']:
                                        ordered_values.append(int(value) if value and value.strip() else None)
                                    else:
                                        ordered_values.append(value)
                                rows_to_insert.append(tuple(ordered_values))
                            
                            if rows_to_insert:
                                cursor.executemany(insert_sql, rows_to_insert)
                    except FileNotFoundError:
                        app.logger.error(f"CSV 文件未找到: {csv_file_path}。跳过对 {table_name} 的数据加载。")
                        pytest.fail(f"测试前置CSV文件未找到: {csv_file_path}")
                    except Exception as e:
                        app.logger.error(f"从 {csv_file_path} 加载数据到 {table_name} 时出错: {e}")
                        pytest.fail(f"测试前置数据加载失败: {e}")
                connection.commit()
    except pymysql.MySQLError as db_e:
        app.logger.error(f"更新测试设置 fixture 期间发生数据库错误: {db_e}")
        pytest.fail(f"更新测试设置期间发生数据库错误: {db_e}")
    except Exception as e:
        app.logger.error(f"更新测试设置 fixture 期间发生一般错误: {e}")
        pytest.fail(f"更新测试设置期间发生一般错误: {e}")
    yield
    app.logger.debug("更新测试函数完成，db_setup_for_update_tests fixture 清理 (如有)。")

# ======== /update_record 端点测试 ========

def test_update_single_field_success(client, db_setup_for_update_tests):
    """
    测试用例 4.1: 成功更新单条记录的单个字段 (users.email)。
    验证状态码 (200)，响应消息，数据库记录是否正确更新。
    """
    user_id_to_update = 2 # 假设用户 ID 2 在 users.csv 中存在
    new_email = "updated.bob@example.com"
    original_username = "bob" # 从 users.csv 中 ID 为 2 的记录获取

    update_payload = {
        "table_name": "users",
        "primary_key": "id",
        "primary_value": user_id_to_update,
        "update_fields": {
            "email": new_email
        }
    }

    response = client.post('/update_record', json=update_payload) # app.py 接受单个对象或列表
    assert response.status_code == 200, f"API 请求失败，状态码: {response.status_code}, 响应: {response.data.decode()}"
    
    data = json.loads(response.data)
    assert isinstance(data, list), "响应应该是一个列表"
    assert len(data) == 1, "响应列表应该包含一个结果对象"
    result = data[0]

    assert result.get("table_name") == "users"
    assert result.get("primary_key") == "id"
    assert result.get("primary_value") == user_id_to_update
    assert result.get("message") == "Record updated successfully", f"未返回预期的成功消息: {result.get('message')}"
    assert "error" not in result, f"响应中不应包含错误: {result.get('error')}"

    # 验证数据库
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT email, username FROM users WHERE id = %s", (user_id_to_update,))
            db_record = cursor.fetchone()
            assert db_record is not None, "数据库中未找到更新后的记录"
            assert db_record["email"] == new_email, "Email 未按预期更新"
            assert db_record["username"] == original_username, "Username 不应被更改" # 确保其他字段未受影响

def test_update_multiple_fields_success(client, db_setup_for_update_tests):
    """
    测试用例 4.2: 成功更新单条记录的多个字段 (users.username 和 users.email)。
    """
    user_id_to_update = 4 # 假设用户 ID 4 (diana) 在 users.csv 中存在
    new_username = "diana_updated"
    new_email = "diana.updated@example.com"
    original_password = "hashed_pw_4" # 从 users.csv 中 ID 为 4 的记录获取

    update_payload = {
        "table_name": "users",
        "primary_key": "id",
        "primary_value": user_id_to_update,
        "update_fields": {
            "username": new_username,
            "email": new_email
            # "updated_at": "NOW()" # 也可以测试 NOW() 函数
        }
    }

    response = client.post('/update_record', json=update_payload)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list) and len(data) == 1
    result = data[0]

    assert result.get("message") == "Record updated successfully"
    assert "error" not in result

    # 验证数据库
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT username, email, password FROM users WHERE id = %s", (user_id_to_update,))
            db_record = cursor.fetchone()
            assert db_record is not None
            assert db_record["username"] == new_username, "Username 未按预期更新"
            assert db_record["email"] == new_email, "Email 未按预期更新"
            assert db_record["password"] == original_password, "Password 不应被更改"

def test_update_non_existent_record(client, db_setup_for_update_tests):
    """
    测试用例 4.3: 更新不存在的记录（基于主键）。
    验证 API 返回 200，但消息表明未找到记录。
    """
    non_existent_user_id = 99999

    update_payload = {
        "table_name": "users",
        "primary_key": "id",
        "primary_value": non_existent_user_id,
        "update_fields": {
            "email": "should.not.matter@example.com"
        }
    }

    response = client.post('/update_record', json=update_payload)
    assert response.status_code == 200, f"API 请求失败，状态码: {response.status_code}, 响应: {response.data.decode()}"
    
    data = json.loads(response.data)
    assert isinstance(data, list) and len(data) == 1
    result = data[0]
    
    # 根据 app.py 的逻辑，当记录未找到时，会返回一个包含 error 键的字典
    assert "error" in result, "当记录未找到时，响应中应包含 'error' 键"
    assert result.get("error") == f"No record found with id={non_existent_user_id}", \
           f"未返回预期的 'No record found' 错误消息: {result.get('error')}"
    assert result.get("message") is None, "当记录未找到时，不应有 'message' 键"
    
    # （可选）可以验证数据库中没有 ID 为 non_existent_user_id 的记录被创建或修改
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE id = %s", (non_existent_user_id,))
            assert cursor.fetchone()["count"] == 0, "不应创建或修改不存在的记录" 


def test_update_violates_unique_constraint(client, db_setup_for_update_tests):
    """
    测试用例 4.4: 更新时违反唯一约束 (users.email)。
    验证 API 返回 500 错误及特定数据库错误 (MySQL 1062)。
    """
    # 从数据库获取两个不同用户的 email 以制造冲突
    # 假设 users.csv 中 id=2 的用户是 bob, id=4 的用户是 diana
    user_a_id = 2 
    user_b_email = "diana.hero@no-prompts.com" # 这是 diana 的 email

    update_payload = {
        "table_name": "users",
        "primary_key": "id",
        "primary_value": user_a_id, # 尝试更新 bob
        "update_fields": {
            "email": user_b_email # 尝试将 bob 的 email 更新为 diana 的 email
        }
    }

    response = client.post('/update_record', json=update_payload)
    assert response.status_code == 500, f"API 未按预期返回500错误，状态码: {response.status_code}, 响应: {response.data.decode()}"
    data = json.loads(response.data)

    assert "error" in data, "响应中缺少 'error' 字段"
    assert "1062" in data["error"], "错误消息应包含 MySQL 唯一约束错误码 1062"
    assert "duplicate entry" in data["error"].lower(), "错误消息应包含 'duplicate entry' (不区分大小写)"
    assert user_b_email.lower() in data["error"].lower(), f"错误消息应包含冲突的 email 值 '{user_b_email}' (不区分大小写)"

def test_update_field_with_now_function(client, db_setup_for_update_tests):
    """
    测试用例 4.5: 更新字段时使用 "NOW()" 函数。
    验证 API 返回 200 成功，并且数据库中的 updated_at 时间戳已更新。
    """
    user_id_to_update = 2 # bob
    original_email_for_bob = "bob@example.com" # 用于验证其他字段未变

    # 为了确保能明确看到 updated_at 的变化，先将其设置为一个较早的时间
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 设置一个比当前时间早1天的时间
            one_day_ago = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("UPDATE users SET updated_at = %s WHERE id = %s", (one_day_ago, user_id_to_update))
            conn.commit()
            # 读取设置后的旧时间，确保它确实被设置了
            cursor.execute("SELECT updated_at FROM users WHERE id = %s", (user_id_to_update,))
            old_updated_at = cursor.fetchone()["updated_at"]
            assert (datetime.utcnow() - old_updated_at).total_seconds() > 3600, "前置更新旧 updated_at 失败或时间差不够大"

    update_payload = {
        "table_name": "users",
        "primary_key": "id",
        "primary_value": user_id_to_update,
        "update_fields": {
            "updated_at": "NOW()"
        }
    }

    response = client.post('/update_record', json=update_payload)
    assert response.status_code == 200, f"API 请求失败，状态码: {response.status_code}, 响应: {response.data.decode()}"
    data = json.loads(response.data)
    assert isinstance(data, list) and len(data) == 1
    result = data[0]
    assert result.get("message") == "Record updated successfully", f"响应消息不正确: {result.get('message')}"

    # 验证数据库中的 updated_at 时间戳
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT email, updated_at FROM users WHERE id = %s", (user_id_to_update,))
            db_record = cursor.fetchone()
            assert db_record is not None, "数据库中未找到更新后的记录"
            assert db_record["email"] == original_email_for_bob, "Email 字段不应被 NOW() 更新操作改变"
            assert isinstance(db_record["updated_at"], datetime), "updated_at 字段不是有效的 datetime 对象"
            
            current_time_utc = datetime.utcnow()
            # 检查更新后的 updated_at 是否晚于之前手动设置的 old_updated_at
            assert db_record["updated_at"] > old_updated_at, "NOW() 更新后的 updated_at 没有晚于之前设置的旧时间"
            # 检查时间戳是否"最近"
            time_difference_updated = current_time_utc - db_record["updated_at"]
            assert abs(time_difference_updated.total_seconds()) < 20, \
                f"updated_at 时间戳 ({db_record['updated_at']}) 与当前UTC时间 ({current_time_utc}) 差距过大，差值: {time_difference_updated.total_seconds()}秒"

def test_update_data_type_mismatch(client, db_setup_for_update_tests):
    """
    测试用例 4.6: 更新时数据类型不匹配。
    场景：尝试将 prompts.user_id (BIGINT) 更新为非数字字符串。
    验证 API 返回 200，但结果对象中包含错误信息。
    """
    # 假设 prompts 表中存在 id 为 9 的记录 (来自 prompts.csv)
    prompt_id_to_update = 9 
    invalid_user_id_value = "not_an_integer"

    update_payload = {
        "table_name": "prompts",
        "primary_key": "id",
        "primary_value": prompt_id_to_update,
        "update_fields": {
            "user_id": invalid_user_id_value 
        }
    }
    
    response = client.post('/update_record', json=update_payload)
    assert response.status_code == 200, f"API请求未按预期返回200，状态码: {response.status_code}, 响应: {response.data.decode()}"
    data = json.loads(response.data)
    assert isinstance(data, list) and len(data) == 1, "响应应为包含一个结果的列表"
    result = data[0]

    assert "error" in result, "当类型不匹配时，结果中应包含 'error' 键"
    assert result.get("table_name") == "prompts"
    assert result.get("primary_key") == "id"
    assert result.get("primary_value") == prompt_id_to_update # 主键值应被回显
    error_message = result.get("error", "").lower() # 转为小写以便不区分大小写的断言
    assert "invalid numeric value" in error_message or "invalid literal for int()" in error_message, \
        f"错误消息未正确指示 user_id 的数字类型问题: {result.get('error')}"
    expected_substring1 = f'"user_id": "{invalid_user_id_value.lower()}"'
    expected_substring2 = f'user_id: {invalid_user_id_value.lower()}'
    assert expected_substring1 in error_message or expected_substring2 in error_message, \
        f"错误消息 '{error_message}' 未包含预期的无效 user_id ('{invalid_user_id_value}') 信息 (预期子串1: '{expected_substring1}', 预期子串2: '{expected_substring2}')"

def test_batch_update_success(client, db_setup_for_update_tests):
    """
    测试用例 4.7: 批量更新操作成功。
    一次请求更新两条不同的用户记录。
    """
    user_a_id = 2 # bob
    new_email_for_a = "bob.updated.batch@example.com"

    user_b_id = 4 # diana
    new_username_for_b = "diana_batch_updated"

    batch_payload = [
        {
            "table_name": "users",
            "primary_key": "id",
            "primary_value": user_a_id,
            "update_fields": {"email": new_email_for_a}
        },
        {
            "table_name": "users",
            "primary_key": "id",
            "primary_value": user_b_id,
            "update_fields": {"username": new_username_for_b}
        }
    ]

    response = client.post('/update_record', json=batch_payload)
    assert response.status_code == 200, f"API 请求失败，状态码: {response.status_code}, 响应: {response.data.decode()}"
    data = json.loads(response.data)

    assert isinstance(data, list), "响应应该是一个列表"
    assert len(data) == 2, "响应列表应该包含两个结果对象"

    # 验证结果对象 A
    result_a = next((r for r in data if r.get("primary_value") == user_a_id), None)
    assert result_a is not None, f"未找到用户 ID {user_a_id} 的更新结果"
    assert result_a.get("message") == "Record updated successfully", f"用户A更新消息不正确: {result_a.get('message')}"
    assert "error" not in result_a

    # 验证结果对象 B
    result_b = next((r for r in data if r.get("primary_value") == user_b_id), None)
    assert result_b is not None, f"未找到用户 ID {user_b_id} 的更新结果"
    assert result_b.get("message") == "Record updated successfully", f"用户B更新消息不正确: {result_b.get('message')}"
    assert "error" not in result_b

    # 验证数据库
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 验证用户 A
            cursor.execute("SELECT email FROM users WHERE id = %s", (user_a_id,))
            db_record_a = cursor.fetchone()
            assert db_record_a is not None
            assert db_record_a["email"] == new_email_for_a, "用户A的Email未按预期批量更新"

            # 验证用户 B
            cursor.execute("SELECT username FROM users WHERE id = %s", (user_b_id,))
            db_record_b = cursor.fetchone()
            assert db_record_b is not None
            assert db_record_b["username"] == new_username_for_b, "用户B的Username未按预期批量更新" 

# === 测试开发总结与问题回顾 ===
# 1. CSV 文件 BOM 问题:
#    - 问题: `db_setup_for_update_tests` fixture 在从 CSV 加载数据时，因 CSV 文件（尤其是 users.csv）的 `id` 字段名包含 UTF-8 BOM (Byte Order Mark) `\\ufeff`，导致列名解析为 `\\ufeffid`，进而引发数据库操作错误 "Unknown column '\ufeffid' in 'field list'"。
#    - 解决: 在读取 CSV 表头 (fieldnames) 后，对每个字段名使用 `name.lstrip('\\ufeff')` 进行清理，移除可能存在的前导 BOM 字符。

# 2. f-string 中的 SyntaxError:
#    - 问题: 在 `test_update_data_type_mismatch` 中，尝试使用类似 `f"key": "{value}"` 的语法直接在 f-string中断言，导致 `SyntaxError: invalid syntax`。
#    - 解决: 将断言修改为先构造期望的子字符串，然后使用 `in` 操作符检查这些子字符串是否存在于错误消息中。例如：
#      `expected_substring1 = f'"user_id": "{invalid_user_id_value.lower()}"'`
#      `assert expected_substring1 in error_message or expected_substring2 in error_message`

# 3. NameError: name 'timedelta' is not defined:
#    - 问题: 在 `test_update_field_with_now_function` 中使用了 `timedelta` 来计算日期差异，但未从 `datetime` 模块导入。
#    - 解决: 在文件顶部添加 `from datetime import datetime, timedelta`。

# 4. 唯一约束断言大小写问题:
#    - 问题: 在 `test_update_violates_unique_constraint` 中，虽然数据库错误消息为 "Duplicate entry..."，但 API 返回的 `data["error"]` 经过 `.lower()` 处理后变为 "duplicate entry..."。原断言 `assert "Duplicate entry" in data["error"].lower()` 因大小写不匹配而失败。
#    - 解决: 将断言修改为 `assert "duplicate entry" in data["error"].lower()`，确保与已转换为小写的错误消息进行比较。

# 5. 文档字符串 (Docstring) 中的 Linter 报错:
#    - 问题: Pylance Linter 报告中文文档字符串存在 "令牌中的字符无效" 或 "语句必须用换行符或分号分隔" 的错误。
#    - 解决: 在所有中文文档字符串的三引号 (`\"\"\"`) 和实际中文文本之间添加一个换行符。例如:
#      `\"\"\"`
#      `中文文档字符串内容`
#      `\"\"\"` 