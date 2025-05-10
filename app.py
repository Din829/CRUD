from flask import Flask, request, jsonify
import pymysql
import logging
import os
from datetime import datetime
from contextlib import contextmanager
import locale  # 新增：支持英文日期解析
import json
from decimal import Decimal
import re # <--- 新增导入
import copy # <--- 新增导入 copy 用于深拷贝操作
# from flask_cors import CORS # <--- 注释掉

app = Flask(__name__)
# CORS(app)  # 注释掉CORS
logging.basicConfig(level=logging.DEBUG)

# 数据库连接上下文管理器
@contextmanager
def get_db_connection():
    connection = pymysql.connect(
        host=os.environ.get('DB_HOST', '127.0.0.1'),
        port=int(os.environ.get('DB_PORT', 33306)),
        user=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', 'q75946123'),
        database=os.environ.get('DB_NAME', 'ai_support_platform_db'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        yield connection
    finally:
        connection.close()

@app.route('/execute_query', methods=['POST'])
def execute_query():
    data = request.get_json()
    sql_query = data.get('sql_query')
    app.logger.debug(f"Received SQL query length: {len(sql_query) if sql_query else 0}")
    if len(sql_query) > 200:
        app.logger.debug(f"Query start: {sql_query[:100]}...")
        app.logger.debug(f"Query end: ...{sql_query[-100:]}")

    if not sql_query:
        return jsonify({"error": "No SQL query provided"}), 400

    # 预处理SQL查询，清理尾部分号和空格以防止空语句错误
    sql_query = sql_query.strip()
    has_trailing_semicolon = sql_query.endswith(';')
    # 先移除所有尾部分号
    while sql_query.endswith(';'):
        sql_query = sql_query[:-1].strip()  # 移除尾部分号并再次清理空格
    
    # 确保处理后的SQL不为空
    if not sql_query:
        return jsonify({"error": "Empty SQL query after processing"}), 400

    # 安全检查：只允许SELECT语句
    if not sql_query.strip().upper().startswith('SELECT'):
        return jsonify({"error": "Only SELECT queries are allowed"}), 403
    
    # 对于MySQL，1064错误通常与语法相关，末尾分号有时是必要的
    # 我们在发送给数据库前添加回分号
    if has_trailing_semicolon:
        sql_query = sql_query + ';'
    
    app.logger.debug(f"Processed SQL query length: {len(sql_query)}")

    with get_db_connection() as connection:
        try:
            cursor = connection.cursor()
            app.logger.debug("Executing SQL query...")
            cursor.execute(sql_query)
            result = cursor.fetchall()
            app.logger.debug(f"Query returned {len(result)} rows")
            
            # 修复: 如果结果为空列表，直接返回空列表
            if not result:
                return jsonify([])
                
            # 我们不再需要手动处理列名，因为DictCursor已经将结果转为字典
            return jsonify(result)

        except Exception as e:
            app.logger.error(f"Error executing query: {e}")
            # 添加更详细的错误信息，特别是对于MySQL 1064错误
            if "1064" in str(e):
                # 特别处理此类常见错误
                app.logger.error(f"MySQL syntax error detected: {e}")
                # 尝试诊断错误更精确位置
                error_match = re.search(r"near '(.*?)' at line (\d+)", str(e))
                if error_match:
                    near_text = error_match.group(1)
                    line_num = error_match.group(2)
                    app.logger.error(f"Syntax error near '{near_text}' at line {line_num}")
                    return jsonify({"error": (1064, f"SQL syntax error near '{near_text}' at line {line_num}")}), 500
            
            return jsonify({"error": e.args}), 500





@app.route('/update_record', methods=['POST'])
def update_record():
    data = request.get_json()
    if isinstance(data, list):
        updates = data
    else:
        updates = [data]

    with get_db_connection() as connection:
        try:
            with connection.cursor() as cursor:
                results = []
                schema_cache = {}
                # 缓存所有表结构
                for update in updates:
                    table_name = update.get('table_name')
                    if table_name not in schema_cache:
                        cursor.execute(f"DESCRIBE {table_name}")
                        schema_cache[table_name] = {row["Field"]: {
                            "type": row["Type"].lower(),
                            "null": row["Null"] == "NO",
                            "key": row["Key"]
                        } for row in cursor.fetchall()}

                for update in updates:
                    table_name = update.get('table_name')
                    primary_key = update.get('primary_key')
                    primary_value = update.get('primary_value')
                    update_fields = update.get('update_fields', {})
                    app.logger.debug(f"Processing update: table={table_name}, {primary_key}={primary_value}, fields={update_fields}")

                    # 校验表名、主键和主键值
                    if not all([table_name, primary_key, primary_value]):
                        results.append({
                            "table_name": table_name,
                            "primary_key": primary_key,
                            "primary_value": primary_value,
                            "error": "Missing table_name, primary_key, or primary_value"
                        })
                        continue

                    schema = schema_cache.get(table_name, {})
                    if not schema:
                        results.append({
                            "table_name": table_name,
                            "primary_key": primary_key,
                            "primary_value": primary_value,
                            "error": "Invalid table name"
                        })
                        continue

                    date_types = ["datetime", "timestamp", "date"]
                    numeric_types = ["int", "tinyint", "bigint", "decimal", "float"]

                    # 校验记录存在
                    cursor.execute(f"SELECT {primary_key} FROM {table_name} WHERE {primary_key} = %s", [primary_value])
                    if not cursor.fetchone():
                        results.append({
                            "table_name": table_name,
                            "primary_key": primary_key,
                            "primary_value": primary_value,
                            "error": f"No record found with {primary_key}={primary_value}"
                        })
                        continue

                    # 校验必需字段
                    required_fields = [
                        field for field, info in schema.items()
                        if info["null"] and field != primary_key and not info["type"].startswith("timestamp")
                    ]
                    missing_fields = [f for f in required_fields if f not in update_fields]
                    if missing_fields:
                        # 尝试从数据库补充缺失字段
                        cursor.execute(f"SELECT {', '.join(missing_fields)} FROM {table_name} WHERE {primary_key} = %s", [primary_value])
                        record = cursor.fetchone()
                        if record:
                            for field in missing_fields:
                                update_fields[field] = record[field]
                        else:
                            results.append({
                                "table_name": table_name,
                                "primary_key": primary_key,
                                "primary_value": primary_value,
                                "error": f"Missing required fields: {', '.join(missing_fields)}"
                            })
                            continue

                    # 构建更新 SQL
                    params = []
                    set_clause_parts = []
                    for field, value in update_fields.items():
                        if field not in schema:
                            continue
                        
                        current_value = value # 保存当前值以添加到 params
                        is_now_function = False

                        if isinstance(value, str) and value.lower() == "now()":
                            set_clause_parts.append(f"{field} = NOW()")
                            is_now_function = True
                        else:
                            set_clause_parts.append(f"{field} = %s")
                            if any(dt in schema[field]["type"] for dt in date_types) and value:
                                # 修复：如果值已经是 datetime 对象，则不调用 parse_date
                                if not isinstance(value, datetime):
                                    try:
                                        # value 是字符串，尝试解析
                                        current_value = parse_date(str(value), schema[field]["type"])
                                    except ValueError as e:
                                        results.append({
                                            "table_name": table_name,
                                            "primary_key": primary_key,
                                            "primary_value": primary_value,
                                            "error": f"Invalid date format for {field}: {value} ({e})"
                                        })
                                        # 出错时跳过此字段的处理，标记错误
                                        current_value = None # 标记此字段处理失败
                                        break # 跳出内层循环，处理下一个字段 (或者 continue?) -> 改为 break 跳出整个记录处理
                                else:
                                     # value 已经是 datetime 对象，current_value 保持不变
                                     pass 
                            elif any(nt in schema[field]["type"] for nt in numeric_types):
                                if isinstance(value, str):
                                    try:
                                        current_value = int(value) if "int" in schema[field]["type"] else float(value)
                                    except ValueError:
                                        results.append({
                                            "table_name": table_name,
                                            "primary_key": primary_key,
                                            "primary_value": primary_value,
                                            "error": f"Invalid numeric value for {field}: {value}"
                                        })
                                        current_value = None
                                        break
                                elif isinstance(value, (int, float, Decimal)):
                                     current_value = value # 已经是有效数字类型，直接使用
                                else: # 其他类型视为无效数字
                                     results.append({
                                            "table_name": table_name,
                                            "primary_key": primary_key,
                                            "primary_value": primary_value,
                                            "error": f"Invalid numeric type for {field}: {type(value)}"
                                        })
                                     current_value = None
                                     break
                            # else: # 其他类型字段，current_value 保持不变
                        
                        # 如果字段处理中发生错误 (current_value is None)，则跳过添加参数
                        if not is_now_function and current_value is not None:
                             params.append(current_value)
                        elif current_value is None: # 发生错误，停止处理此记录
                             break # 跳出 for field, value 循环
                    
                    # 检查内层循环是否因为错误而 break
                    if current_value is None: 
                         continue # 继续处理下一个 update 记录

                    # 处理主键类型
                    if any(nt in schema.get(primary_key, {}).get("type", "") for nt in numeric_types) and isinstance(primary_value, str):
                        try:
                            primary_value = int(primary_value)
                        except ValueError:
                            results.append({
                                "table_name": table_name,
                                "primary_key": primary_key,
                                "primary_value": primary_value,
                                "error": f"Invalid {primary_key} format"
                            })
                            continue

                    set_clause = ", ".join(set_clause_parts)
                    params.append(primary_value)
                    sql_query = f"UPDATE {table_name} SET {set_clause} WHERE {primary_key} = %s"
                    app.logger.debug(f"Executing SQL: {sql_query} with params: {params}")
                    cursor.execute(sql_query, params)
                    affected_rows = cursor.rowcount

                    if affected_rows > 0:
                        results.append({
                            "table_name": table_name,
                            "primary_key": primary_key,
                            "primary_value": primary_value,
                            "message": "Record updated successfully"
                        })
                    else:
                        results.append({
                            "table_name": table_name,
                            "primary_key": primary_key,
                            "primary_value": primary_value,
                            "message": "Record unchanged"
                        })

                connection.commit()
                app.logger.debug(f"Batch update completed: {results}")
                return jsonify(results)
        except Exception as e:
            connection.rollback()
            app.logger.error(f"Error updating records: {str(e)}")
            return jsonify({"error": str(e)}), 500


@app.route('/insert_record', methods=['POST'])
def insert_record():
    raw_data = request.get_data(as_text=True)
    app.logger.debug(f"Raw request data: {raw_data}")
    
    try:
        data = json.loads(raw_data) if raw_data else request.get_json()
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON decode error: {str(e)}")
        return jsonify({"error": f"Invalid JSON format: {str(e)}"}), 400
    
    app.logger.debug(f"Parsed JSON data: {data}")

    # 确保输入是列表格式
    if isinstance(data, dict):
        # 兼容 LLM 直接输出 {"table": [fields]} 或 {"result": {"table": [fields]}} 的情况
        if "result" in data and isinstance(data["result"], dict):
             data_to_process = data["result"]
        else:
             data_to_process = data
        
        records = []
        for table_name, fields_list in data_to_process.items():
             if isinstance(fields_list, list):
                  for fields in fields_list:
                       records.append({"table_name": table_name, "fields": fields})
             elif isinstance(fields_list, dict): # 处理单个记录的情况
                  records.append({"table_name": table_name, "fields": fields_list})
    elif isinstance(data, list):
        records = data # 假设列表内已经是 { "table_name": ..., "fields": ...} 格式
    else:
        return jsonify({"error": "Request body must be a list or dict representing records"}), 400


    if not records:
        return jsonify({"error": "No records provided"}), 400

    with get_db_connection() as connection:
        try:
            with connection.cursor() as cursor:
                connection.begin() # 显式开启事务

                results = []
                generated_keys = {} # 存储生成的主键: {"table_name.pk_name": pk_value}
                schema_cache = {} # 缓存表结构
                
                # --- 预缓存所有涉及表的 Schema ---
                all_table_names = set(r.get("table_name") for r in records if isinstance(r, dict) and r.get("table_name"))
                for table_name in all_table_names:
                    if table_name not in schema_cache:
                         try:
                              cursor.execute(f"DESCRIBE `{table_name}`") # 使用反引号处理特殊表名
                              schema_cache[table_name] = {row["Field"]: {
                                   "type": row["Type"].lower(),
                                   "null": row["Null"],
                                   "key": row["Key"],
                                   "default": row["Default"],
                                   "extra": row.get("Extra", "") # 获取 Extra 信息 (包含 auto_increment)
                              } for row in cursor.fetchall()}
                              app.logger.debug(f"Cached schema for table: {table_name}")
                         except Exception as e:
                              raise ValueError(f"Failed to get schema for table '{table_name}': {e}")

                # 定义占位符正则
                NEW_PLACEHOLDER_PATTERN = re.compile(r'\{\{new\(([^)]+)\)\}\}')

                # --- 分离独立记录和依赖记录 ---
                independent_records = []
                dependent_records = []
                for record in records:
                    has_dependency = False
                    if isinstance(record, dict) and "fields" in record and isinstance(record["fields"], dict):
                        for value in record["fields"].values():
                            if isinstance(value, str) and NEW_PLACEHOLDER_PATTERN.search(value):
                                has_dependency = True
                                break
                    if has_dependency:
                        dependent_records.append(record)
                    else:
                        independent_records.append(record)
                
                app.logger.debug(f"Independent records: {len(independent_records)}")
                app.logger.debug(f"Dependent records: {len(dependent_records)}")

                # --- 辅助函数：执行单条插入并记录主键 ---
                def execute_single_insert(record_data, current_generated_keys):
                    table_name = record_data.get("table_name")
                    fields = record_data.get("fields", {})
                    
                    if not table_name or not fields:
                        raise ValueError(f"Invalid record data: {record_data}")

                    schema = schema_cache.get(table_name)
                    if not schema:
                        raise ValueError(f"Schema not found for table: {table_name}")

                    primary_key = next((f for f, v in schema.items() if v["key"] == "PRI"), None)
                    if not primary_key:
                        raise ValueError(f"No primary key found for table {table_name}")
                    
                    is_auto_increment = "auto_increment" in schema.get(primary_key, {}).get("extra", "")

                    # 处理占位符替换 (仅对依赖记录有效，独立记录此循环为空)
                    resolved_fields = {}
                    for field, value in fields.items():
                         if field not in schema:
                              app.logger.warning(f"Field '{field}' not found in schema for table '{table_name}', skipping.")
                              continue
                         
                         resolved_value = value
                         if isinstance(value, str):
                              match = NEW_PLACEHOLDER_PATTERN.search(value)
                              if match:
                                   dependency_key = match.group(1).strip() # e.g., "users.id"
                                   if dependency_key in current_generated_keys:
                                        actual_id = current_generated_keys[dependency_key]
                                        resolved_value = actual_id # 替换占位符
                                        app.logger.debug(f"Resolved placeholder '{value}' to '{actual_id}' for field '{field}'")
                                   else:
                                        # 如果在这里找不到，说明依赖的记录处理出错或顺序错误
                                        raise ValueError(f"Unresolved dependency: Placeholder '{value}' found, but key '{dependency_key}' not found in generated keys. Ensure records are ordered correctly or dependency exists.")
                         resolved_fields[field] = resolved_value

                    # 日期和 NOW() 处理
                    date_types = ["datetime", "timestamp", "date"]
                    numeric_types = ["int", "tinyint", "bigint", "decimal", "float"]
                    params = []
                    columns = []
                    
                    # 如果是自增主键且用户未提供，则不加入插入列
                    if is_auto_increment and primary_key not in resolved_fields:
                        app.logger.debug(f"Skipping auto-increment primary key '{primary_key}' in insert statement.")
                        fields_to_insert = {k: v for k, v in resolved_fields.items() if k != primary_key}
                    else:
                        fields_to_insert = resolved_fields
                        # 如果是非自增主键但用户未提供，这里需要处理（例如报错或尝试生成）
                        # 目前假设非自增主键必须在 resolved_fields 中提供

                    for field, value in fields_to_insert.items():
                         if field not in schema: continue # Double check schema

                         field_type = schema[field]["type"]
                         param_value = value # 默认使用解析后的值

                         # 处理日期和 NOW()
                         if any(dt in field_type for dt in date_types) and param_value:
                              if isinstance(param_value, str) and param_value.lower() == "now()":
                                   pass # 特殊处理 NOW()，不在 params 中添加
                              elif not isinstance(param_value, datetime): # 检查是否已是 datetime 对象
                                   try:
                                        param_value = parse_date(str(param_value).strip(), field_type)
                                   except ValueError as e:
                                        raise ValueError(f"Invalid date format for field '{field}': {param_value} - {e}")
                         # 处理数字类型转换 (如果需要)
                         elif any(nt in field_type for nt in numeric_types) and param_value is not None:
                              if isinstance(param_value, str):
                                   try:
                                        param_value = int(param_value) if "int" in field_type else float(param_value)
                                   except ValueError:
                                        raise ValueError(f"Invalid numeric value for field '{field}': {param_value}")
                              elif not isinstance(param_value, (int, float, Decimal)):
                                   raise ValueError(f"Invalid numeric type for field '{field}': {type(param_value)}")
                         
                         # 添加列和参数 (除了 NOW())
                         if not (isinstance(param_value, str) and param_value.lower() == "now()"):
                             columns.append(f"`{field}`") # 使用反引号
                             params.append(param_value)
                         else:
                             # 如果是 NOW(), 只添加列名
                             columns.append(f"`{field}`")

                    # 构建 SQL，特殊处理 NOW()
                    value_placeholders = []
                    final_params = []
                    param_idx = 0
                    for field_name in columns:
                         original_value = fields_to_insert.get(field_name.strip('`')) # 获取原始值检查是否是 NOW()
                         if isinstance(original_value, str) and original_value.lower() == "now()":
                              value_placeholders.append("NOW()")
                         else:
                              value_placeholders.append("%s")
                              final_params.append(params[param_idx])
                              param_idx += 1

                    sql_query = f"INSERT INTO `{table_name}` ({', '.join(columns)}) VALUES ({', '.join(value_placeholders)})"
                    app.logger.debug(f"Executing SQL: {sql_query} with values: {final_params}")
                    cursor.execute(sql_query, final_params)

                    # --- 获取并记录新插入的主键值 ---
                    inserted_id = None
                    if is_auto_increment:
                         try:
                              cursor.execute("SELECT LAST_INSERT_ID()")
                              result = cursor.fetchone()
                              if result and result['LAST_INSERT_ID()'] is not None and int(result['LAST_INSERT_ID()']) > 0:
                                   inserted_id = result['LAST_INSERT_ID()']
                                   app.logger.debug(f"Retrieved LAST_INSERT_ID(): {inserted_id}")
                              else:
                                   app.logger.warning("LAST_INSERT_ID() returned 0 or None, check PK definition.")
                         except Exception as e:
                              app.logger.warning(f"Failed to execute SELECT LAST_INSERT_ID(): {e}")
                    else:
                         # 对于非自增主键，从解析后的字段中获取值
                         inserted_id = resolved_fields.get(primary_key)
                         if inserted_id is not None:
                              app.logger.debug(f"Using provided non-auto-increment PK value: {inserted_id}")
                         else:
                              app.logger.warning(f"Could not get PK value from fields for non-auto-increment PK: {primary_key}")

                    # 存储生成的键值，供后续记录引用
                    if inserted_id is not None:
                         key_for_lookup = f"{table_name}.{primary_key}"
                         current_generated_keys[key_for_lookup] = inserted_id
                         app.logger.debug(f"Stored generated key: {key_for_lookup} = {inserted_id}")
                         return {"message": f"Record inserted into {table_name}: {primary_key}={inserted_id}", "generated_id": inserted_id}
                    else:
                         app.logger.warning(f"Could not determine inserted ID for {table_name}.{primary_key}")
                         return {"message": f"Record inserted into {table_name}, but failed to retrieve ID."}

                # --- 1. 插入独立记录 ---
                for record in independent_records:
                     try:
                          result = execute_single_insert(record, generated_keys)
                          results.append(result["message"])
                     except ValueError as ve:
                          raise ValueError(f"Error processing independent record {record}: {ve}")

                # --- 2. 插入依赖记录 ---
                # TODO: 需要考虑依赖的顺序，如果 dependent_records 之间有依赖，这个简单循环可能不够
                # 简单的拓扑排序或多次迭代可能需要
                # 目前假设依赖只存在于 independent -> dependent
                processed_dependent_count = 0
                max_passes = len(dependent_records) + 1 # 防止无限循环
                current_pass = 0
                
                remaining_dependent = list(dependent_records) # 创建副本以进行迭代修改

                while remaining_dependent and current_pass < max_passes:
                    current_pass += 1
                    app.logger.debug(f"--- Processing dependent records pass {current_pass}, remaining: {len(remaining_dependent)} ---")
                    inserted_in_pass = 0
                    next_remaining = []

                    for record in remaining_dependent:
                         try:
                              # 尝试解析和插入
                              result = execute_single_insert(record, generated_keys)
                              results.append(result["message"])
                              inserted_in_pass += 1
                         except ValueError as ve:
                              # 如果是未解决的依赖错误，则保留到下一轮
                              if "Unresolved dependency" in str(ve):
                                   app.logger.debug(f"Deferring record due to unresolved dependency: {record}")
                                   next_remaining.append(record)
                              else:
                                   # 如果是其他错误（如日期格式），则直接抛出
                                   raise ValueError(f"Error processing dependent record {record}: {ve}")
                    
                    remaining_dependent = next_remaining # 更新剩余列表
                    
                    # 如果这一轮没有成功插入任何记录，并且还有剩余，说明存在循环依赖或无法解决的依赖
                    if inserted_in_pass == 0 and remaining_dependent:
                         raise ValueError(f"Could not resolve dependencies for remaining records after {current_pass} passes: {remaining_dependent}")
                
                # 检查最终是否所有依赖记录都被处理
                if remaining_dependent:
                     raise ValueError(f"Failed to insert all dependent records. Unresolved: {remaining_dependent}")


                # --- 提交事务 ---
                connection.commit()
                app.logger.debug(f"Transaction committed. Final generated keys: {generated_keys}")
                # 返回成功信息
                # 注意：这里的 inserted_records 可能不准确，因为它基于原始输入
                # 返回 generated_keys 可能更有用
                return jsonify({
                    "message": "\n".join(results),
                    "generated_keys": generated_keys 
                    # "inserted_records": [r.get("fields") for r in records if isinstance(r, dict)] # 旧逻辑，可能不准确
                })

        except ValueError as ve: # 捕获处理过程中的 ValueError
             connection.rollback()
             app.logger.error(f"Data validation or processing error: {str(ve)}")
             return jsonify({"error": f"Data Error: {str(ve)}"}), 400 # 返回 400 Bad Request
        except Exception as e:
            connection.rollback()
            app.logger.error(f"Error inserting records: {str(e)}")
            return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


@app.route('/get_schema', methods=['GET'])
def get_schema():
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                db_name = connection.db.decode() if isinstance(connection.db, bytes) else connection.db
                tables = [row[f"Tables_in_{db_name}"] for row in cursor.fetchall()]
                schema = {}
                for table in tables:
                    cursor.execute(f"DESCRIBE `{table}`")
                    schema[table] = {
                        "fields": {
                            field["Field"]: {
                                "type": field["Type"],
                                "null": field["Null"],
                                "key": field["Key"],
                                "default": field["Default"]
                            } for field in cursor.fetchall()
                        },
                        "foreign_keys": {}
                    }
                app.logger.debug(f"Schema retrieved for {db_name}: {len(schema)} tables")
                return jsonify({"result": [json.dumps(schema, ensure_ascii=False)]})
    except pymysql.err.OperationalError as e:
        app.logger.error(f"Database connection error in /get_schema: {str(e)}")
        return jsonify({"error": f"Database connection failed: {str(e)}"}), 500
    except Exception as e:
        app.logger.error(f"Error fetching schema: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred while fetching schema: {str(e)}"}), 500



@app.route('/delete_record', methods=['POST'])
def delete_record():
    data = request.get_json()
    table_name = data.get('table_name')
    primary_key = data.get('primary_key')
    primary_value = data.get('primary_value')
    app.logger.debug(f"Received delete request: table={table_name}, {primary_key}={primary_value}")

    # 参数校验保持不变
    if not all([table_name, primary_key, primary_value]):
        return jsonify({"error": "table_name, primary_key, and primary_value are required"}), 400

    # 使用数据库连接上下文管理器
    with get_db_connection() as connection:
        try:
            with connection.cursor() as cursor:
                # 开始事务（显式声明，虽然 PyMySQL 默认每个 execute 是一个事务，但这里为了清晰性）
                connection.begin()  # 显式开启事务

                # 执行删除操作，原有逻辑不变
                sql_query = f"DELETE FROM {table_name} WHERE {primary_key} = %s"
                cursor.execute(sql_query, (primary_value,))
                affected_rows = cursor.rowcount

                # 提交事务
                connection.commit()
                
                # 返回结果，修改状态码为200，但内容区分是否实际删除了记录
                if affected_rows > 0:
                    app.logger.debug(f"Deleted record in {table_name}: {primary_key}={primary_value}")
                    return jsonify({"message": f"Record with {primary_key}={primary_value} deleted successfully"})
                else:
                    app.logger.debug(f"No record found with {primary_key}={primary_value} in {table_name}")
                    return jsonify({"message": f"No record found with {primary_key}={primary_value} in {table_name}, but operation completed successfully"}), 200

        except Exception as e:
            # 异常时回滚事务
            connection.rollback()
            app.logger.error(f"Error deleting record: {str(e)}")
            return jsonify({"error": str(e)}), 500


@app.route('/export_to_txt', methods=['GET'])
def export_to_txt():
    output_file = "sky_take_out_export.txt"
    
    with get_db_connection() as connection:
        try:
            with connection.cursor() as cursor:
                # 获取所有表名
                cursor.execute("SHOW TABLES")
                tables = [row[f"Tables_in_{connection.db.decode()}"] for row in cursor.fetchall()]
                
                # 打开文件写入
                with open(output_file, 'w', encoding='utf-8') as f:
                    # 导出表结构
                    for table in tables:
                        cursor.execute(f"SHOW CREATE TABLE {table}")
                        create_table = cursor.fetchone()['Create Table']
                        f.write(f"\n-- Table structure for {table}\n")
                        f.write(f"{create_table};\n\n")
                    
                    # 导出表数据
                    for table in tables:
                        f.write(f"\n-- Data for {table}\n")
                        cursor.execute(f"SELECT * FROM {table}")
                        rows = cursor.fetchall()
                        if not rows:
                            f.write("No data\n\n")
                            continue
                        # 写入列名
                        columns = list(rows[0].keys())
                        f.write(','.join(columns) + '\n')
                        # 写入数据
                        for row in rows:
                            # 处理特殊字符和空值
                            values = [str(row[col]).replace(',', '\\,') if row[col] is not None else '' for col in columns]
                            f.write(','.join(values) + '\n')
                        f.write('\n')
                
                return jsonify({"message": f"Database exported to {output_file}"})
        except Exception as e:
            app.logger.error(f"Error exporting database: {str(e)}")
            return jsonify({"error": str(e)}), 500


# 日期解析辅助函数
def parse_date(date_str, field_type):
    try:
        # 设置英文语言环境以支持缩写
        locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')
        formats = [
            '%Y年%m月%d日 %H:%M:%S GMT',  # 2024年11月2日 00:00:00 GMT
            '%a, %d %b %Y %H:%M:%S GMT',  # Fri, 21 Feb 2025 00:00:00 GMT
            '%Y-%m-%d',                   # 2025-02-21
            '%Y/%m/%d',                   # 2025/02/21
            '%Y-%m-%d %H:%M:%S'           # 2025-02-21 00:00:00
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # 根据字段类型返回不同格式
                if "date" in field_type and "datetime" not in field_type:
                    return dt.strftime('%Y-%m-%d')  # DATE 类型
                else:
                    return dt.strftime('%Y-%m-%d %H:%M:%S')  # DATETIME 或 TIMESTAMP
            except ValueError:
                continue
        raise ValueError(f"Unsupported date format: {date_str}")
    except Exception as e:
        raise ValueError(f"Invalid date format: {str(e)}")

# === 新增：批量操作 API 端点 ===

@app.route('/execute_batch_operations', methods=['POST'])
def execute_batch_operations():
    """
    执行一个包含多个数据库操作（insert, update, delete）的列表。
    支持操作间的依赖关系。所有操作在一个事务中执行。
    """
    raw_data = request.get_data(as_text=True)
    app.logger.debug(f"Raw request data for batch operations: {raw_data}")

    try:
        operations = json.loads(raw_data) if raw_data else request.get_json()
        if not isinstance(operations, list):
            return jsonify({"error": "Request body must be a JSON list of operations"}), 400
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON decode error for batch operations: {str(e)}")
        return jsonify({"error": f"Invalid JSON format: {str(e)}"}), 400

    if not operations:
         return jsonify({"message": "Received empty operations list, nothing to execute.", "results": []}), 200

    operation_results_cache = {} 
    batch_results = [] 
    schema_cache = {}

    with get_db_connection() as connection:
        try:
            connection.begin() 
            with connection.cursor() as cursor:
                # === Schema 预缓存 ===
                all_involved_table_names = set()
                for op_for_schema in operations:
                    table_name_for_schema = op_for_schema.get("table_name")
                    if table_name_for_schema:
                        all_involved_table_names.add(table_name_for_schema)
                for t_name in all_involved_table_names:
                    if t_name not in schema_cache:
                        try:
                            cursor.execute(f"DESCRIBE `{t_name}`")
                            schema_cache[t_name] = {row["Field"]: {
                                "type": row["Type"].lower(), "null": row["Null"],
                                "key": row["Key"], "default": row["Default"],
                                "extra": row.get("Extra", "")
                            } for row in cursor.fetchall()}
                            app.logger.info(f"Pre-cached schema for table: {t_name}")
                        except Exception as schema_e:
                            raise ValueError(f"Failed to pre-cache schema for table '{t_name}': {schema_e}")

                # === 主循环处理操作 ===
                for index, op_original in enumerate(operations):
                    op = copy.deepcopy(op_original) # 处理每个操作的拷贝，防止修改影响原始列表
                    app.logger.info(f"Processing operation {index}: {op}")
                    
                    execute_this_op = True # 标记是否需要执行当前原始操作（如果被展开则设为 False）
                    expanded_op_results = [] # 存储展开操作的结果

                    # --- 依赖处理 --- 
                    depends_on_index = op.get("depends_on_index")
                    dependent_result_list = None # 用于存储多行依赖结果

                    if depends_on_index is not None:
                        if not isinstance(depends_on_index, int) or depends_on_index < 0 or depends_on_index >= index:
                            current_op_index_for_error = index
                            raise ValueError(f"Op {index}: Invalid depends_on_index: {depends_on_index}")
                        
                        base_dependent_result = operation_results_cache.get(depends_on_index)
                        if base_dependent_result is None:
                            current_op_index_for_error = index
                            raise ValueError(f"Op {index}: Dependency result not found for index {depends_on_index}")

                        # --- 函数：递归替换占位符 (现在接受单个结果项) ---
                        def replace_placeholders_recursive(item, single_dep_result, current_op_index):
                            if isinstance(item, dict):
                                return {k: replace_placeholders_recursive(v, single_dep_result, current_op_index) for k, v in item.items()}
                            elif isinstance(item, list):
                                return [replace_placeholders_recursive(elem, single_dep_result, current_op_index) for elem in item]
                            elif isinstance(item, str):
                                match = re.match(r"\{\{previous_result\[(\d+)\]\.(\w+)\}\}", item)
                                if match:
                                    dep_idx_str, field_name = match.groups()
                                    dep_idx = int(dep_idx_str)
                                    if dep_idx == depends_on_index:
                                        if isinstance(single_dep_result, dict) and field_name in single_dep_result:
                                            replaced_value = single_dep_result[field_name]
                                            app.logger.info(f"Op {current_op_index}: Replaced '{item}' with '{replaced_value}' from op {depends_on_index}")
                                            return replaced_value
                                        else:
                                            raise ValueError(f"Op {current_op_index}: Field '{field_name}' not found in single dependency result: {single_dep_result}")
                                    else:
                                        raise ValueError(f"Op {current_op_index}: Placeholder index {dep_idx} != depends_on_index {depends_on_index}")
                                return item
                            else:
                                return item
                        # --- END 函数定义 ---
                        
                        # --- 检查依赖结果是否是列表 (多行) ---
                        if isinstance(base_dependent_result, list):
                            app.logger.info(f"Op {index}: Dependency result from op {depends_on_index} is a list (count: {len(base_dependent_result)}). Expanding execution.")
                            execute_this_op = False # 原始操作不再执行，将被展开的操作替代
                            dependent_result_list = base_dependent_result # 保存列表以供循环
                        else:
                            # 单行结果或非预期格式，按单次执行处理
                            # 解析占位符 (针对单个结果)
                            op['values'] = replace_placeholders_recursive(op.get('values'), base_dependent_result, index) if op.get('operation') == 'insert' else op.get('values')
                            if op.get('operation') == 'update':
                                op['set'] = replace_placeholders_recursive(op.get('set'), base_dependent_result, index)
                                op['where'] = replace_placeholders_recursive(op.get('where'), base_dependent_result, index)
                            elif op.get('operation') == 'delete':
                                op['where'] = replace_placeholders_recursive(op.get('where'), base_dependent_result, index)
                            app.logger.debug(f"Op {index}: Operation after single dependency resolution: {op}")
                    
                    # --- 执行操作 (可能是单个，也可能是展开后的多个) ---
                    # 定义内部执行函数，以复用 SQL 构建和执行逻辑
                    def _execute_single_op(operation_data, current_index, current_cursor, current_cache, is_expanded=False, expansion_item_index=None):
                        op_type = operation_data.get("operation", "").lower()
                        op_table = operation_data.get("table_name")
                        op_schema = current_cache.get(op_table)
                        if not op_schema: raise ValueError(f"Op {current_index}: Schema not found for {op_table}")
                        
                        _affected_rows = 0
                        _last_insert_id = None
                        _current_op_result = {}
                        _sql = ""
                        _params = []

                        # --- 函数：准备参数值（移到内部，方便访问 op_schema 和 index）---
                        def prepare_param_value(column_name, value):
                            if column_name not in op_schema:
                                app.logger.warning(f"Op {current_index}: Column '{column_name}' not found in schema for table '{op_table}', skipping type conversion.")
                                return value
                            col_info = op_schema[column_name]; col_type = col_info["type"].lower()
                            date_types = ["datetime", "timestamp", "date"]; numeric_types = ["int", "tinyint", "bigint", "decimal", "float"]
                            if any(dt in col_type for dt in date_types):
                                if isinstance(value, str) and value: 
                                    try: return parse_date(value.strip(), col_type)
                                    except ValueError as date_e: raise ValueError(f"Op {current_index}: Invalid date format for '{column_name}': '{value}' - {date_e}")
                                elif isinstance(value, datetime): return value
                                elif value is None and col_info.get('null') == 'YES': return None
                                else: raise ValueError(f"Op {current_index}: Invalid type/null for date '{column_name}': {type(value)}")
                            elif any(nt in col_type for nt in numeric_types):
                                if isinstance(value, str) and value:
                                    try: return int(value) if "int" in col_type or "bigint" in col_type or "tinyint" in col_type else float(value)
                                    except ValueError: raise ValueError(f"Op {current_index}: Invalid numeric value for '{column_name}': '{value}'")
                                elif isinstance(value, (int, float, Decimal)): return value
                                elif value is None and col_info.get('null') == 'YES': return None
                                else: raise ValueError(f"Op {current_index}: Invalid type/null for numeric '{column_name}': {type(value)}")
                            return value
                        # --- END prepare_param_value ---

                        if op_type == "insert":
                            values_dict = operation_data.get("values")
                            if not isinstance(values_dict, dict): raise ValueError(f"Op {current_index} (insert): 'values' must be dict.")
                            cols, ph, params_insert = [], [], []
                            for c, v in values_dict.items():
                                if c not in op_schema: app.logger.warning(f"Op {current_index}: Insert column '{c}' not in schema, skipping."); continue
                                cols.append(f"`{c}`")
                                if isinstance(v, str) and v.lower() == "now()": ph.append("NOW()")
                                else: ph.append("%s"); params_insert.append(prepare_param_value(c, v))
                            _sql = f"INSERT INTO `{op_table}` ({', '.join(cols)}) VALUES ({', '.join(ph)})"
                            _params = params_insert
                        elif op_type == "update":
                            where_dict = operation_data.get("where"); set_dict = operation_data.get("set")
                            if not isinstance(where_dict, dict) or not where_dict: raise ValueError(f"Op {current_index} (update): 'where' empty.")
                            if not isinstance(set_dict, dict) or not set_dict: raise ValueError(f"Op {current_index} (update): 'set' empty.")
                            s_parts, p_set = [], []
                            for c, v in set_dict.items():
                                if c not in op_schema: app.logger.warning(f"Op {current_index}: Update SET col '{c}' not in schema, skipping."); continue
                                if isinstance(v, str) and v.lower() == "now()": s_parts.append(f"`{c}` = NOW()")
                                elif isinstance(v, str) and (v.strip().upper().startswith(("CONCAT(", "SUBSTRING_INDEX(")) or re.match(r"^\w+\s*[+-]\s*\d+$", v.strip())):
                                    s_parts.append(f"`{c}` = {v}")
                                else: s_parts.append(f"`{c}` = %s"); p_set.append(prepare_param_value(c, v))
                            s_clause = ", ".join(s_parts)
                            w_parts, p_where = [], []
                            for c, cond in where_dict.items():
                                if c not in op_schema: app.logger.warning(f"Op {current_index}: Update WHERE col '{c}' not in schema, skipping."); continue
                                if isinstance(cond, dict):
                                    for opk, opv in cond.items():
                                        sop = opk.upper().strip(); sop_list = [">", "<", ">=", "<=", "LIKE", "IN", "NOT IN", "BETWEEN", "="]
                                        if sop not in sop_list: raise ValueError(f"Op {current_index}: Unsupported operator '{sop}'")
                                        if sop in ["IN", "NOT IN"]:
                                            if not isinstance(opv, list): raise ValueError(f"Op {current_index}: Value for {sop} must be list.")
                                            if not opv: w_parts.append("1=0" if sop == "IN" else "1=1")
                                            else: w_parts.append(f"`{c}` {sop} ({', '.join(['%s']*len(opv))})"); p_where.extend([prepare_param_value(c, item) for item in opv])
                                        elif sop == "BETWEEN":
                                            if not isinstance(opv, list) or len(opv)!=2: raise ValueError(f"Op {current_index}: Value for BETWEEN must be list of 2.")
                                            w_parts.append(f"`{c}` BETWEEN %s AND %s"); p_where.extend([prepare_param_value(c, item) for item in opv])
                                        else: w_parts.append(f"`{c}` {sop} %s"); p_where.append(prepare_param_value(c, opv))
                                else: w_parts.append(f"`{c}` = %s"); p_where.append(prepare_param_value(c, cond))
                            if not w_parts: raise ValueError(f"Op {current_index} (update): WHERE clause empty after processing.")
                            w_clause = " AND ".join(w_parts)
                            _sql = f"UPDATE `{op_table}` SET {s_clause} WHERE {w_clause}"
                            _params = p_set + p_where
                        elif op_type == "delete":
                            where_dict = operation_data.get("where")
                            if not isinstance(where_dict, dict) or not where_dict: raise ValueError(f"Op {current_index} (delete): 'where' empty.")
                            w_parts, p_where = [], []
                            for c, cond in where_dict.items():
                                if c not in op_schema: app.logger.warning(f"Op {current_index}: Delete WHERE col '{c}' not in schema, skipping."); continue
                                if isinstance(cond, dict):
                                    for opk, opv in cond.items():
                                        sop = opk.upper().strip(); sop_list = [">", "<", ">=", "<=", "LIKE", "IN", "NOT IN", "BETWEEN", "="]
                                        if sop not in sop_list: raise ValueError(f"Op {current_index}: Unsupported operator '{sop}'")
                                        if sop in ["IN", "NOT IN"]:
                                            if not isinstance(opv, list): raise ValueError(f"Op {current_index}: Value for {sop} must be list.")
                                            if not opv: w_parts.append("1=0" if sop == "IN" else "1=1")
                                            else: w_parts.append(f"`{c}` {sop} ({', '.join(['%s']*len(opv))})"); p_where.extend([prepare_param_value(c, item) for item in opv])
                                        elif sop == "BETWEEN":
                                            if not isinstance(opv, list) or len(opv)!=2: raise ValueError(f"Op {current_index}: Value for BETWEEN must be list of 2.")
                                            w_parts.append(f"`{c}` BETWEEN %s AND %s"); p_where.extend([prepare_param_value(c, item) for item in opv])
                                        else: w_parts.append(f"`{c}` {sop} %s"); p_where.append(prepare_param_value(c, opv))
                                else: w_parts.append(f"`{c}` = %s"); p_where.append(prepare_param_value(c, cond))
                            if not w_parts: raise ValueError(f"Op {current_index} (delete): WHERE clause empty after processing.")
                            w_clause = " AND ".join(w_parts)
                            _sql = f"DELETE FROM `{op_table}` WHERE {w_clause}"
                            _params = p_where
                        else:
                            raise ValueError(f"Op {current_index}: Unsupported operation type '{op_type}'.")
                        
                        # 执行 SQL
                        exec_msg_prefix = f"Op {current_index}" + (f" (Expanded {expansion_item_index+1})" if is_expanded else "")
                        app.logger.debug(f"{exec_msg_prefix}: Executing SQL: {_sql} with params: {_params}")
                        current_cursor.execute(_sql, _params)
                        _affected_rows = current_cursor.rowcount
                        if op_type == "insert": _last_insert_id = current_cursor.lastrowid
                        
                        # 处理 return_affected
                        return_fields = operation_data.get("return_affected")
                        if _affected_rows > 0 and isinstance(return_fields, list) and return_fields:
                            # --- 修改: 获取所有行的 return_affected 值 --- 
                            pk_name = next((f for f, v in op_schema.items() if v["key"] == "PRI"), None)
                            query_cols = [f for f in return_fields if f in op_schema]
                            if pk_name or op_type == "update" or op_type == "delete": # 需要条件来定位
                                query_cols_str = ", ".join([f"`{c}`" for c in query_cols])
                                if query_cols_str: # 确保有有效的列
                                    fetch_sql = ""
                                    fetch_params = []
                                    if op_type == "insert" and pk_name and _last_insert_id is not None:
                                        fetch_sql = f"SELECT {query_cols_str} FROM `{op_table}` WHERE `{pk_name}` = %s"
                                        fetch_params = [_last_insert_id]
                                    elif op_type == "update" or op_type == "delete":
                                        fetch_sql = f"SELECT {query_cols_str} FROM `{op_table}` WHERE {w_clause}"
                                        fetch_params = p_where # 使用 WHERE 的参数
                                    
                                    if fetch_sql:
                                        app.logger.debug(f"{exec_msg_prefix}: Fetching affected: {fetch_sql} PARAMS: {fetch_params}")
                                        current_cursor.execute(fetch_sql, fetch_params)
                                        # --- 修改: 使用 fetchall() 并处理结果 --- 
                                        fetched_results_list = current_cursor.fetchall() # 获取所有行
                                        if fetched_results_list:
                                             # 如果只影响了一行，或者只关心第一行，可以取 fetched_results_list[0]
                                             # 为了支持后续操作可能依赖多行结果，我们将整个列表存储
                                             _current_op_result = fetched_results_list if len(fetched_results_list) > 1 else fetched_results_list[0]
                                             app.logger.info(f"{exec_msg_prefix}: Fetched affected result: {_current_op_result}")
                                        else:
                                             app.logger.warning(f"{exec_msg_prefix}: Could not fetch affected fields.")
                                else:
                                    app.logger.warning(f"{exec_msg_prefix}: No valid columns in return_affected or missing condition for fetch.")
                            else:
                                app.logger.warning(f"{exec_msg_prefix}: Could not determine PK for table {op_table} or invalid state for fetching return_affected.")
                        
                        # 返回执行结果和可能获取到的数据
                        return {
                            "step_result": {
                                "operation_index": current_index, # 保留原始索引
                                "expansion_index": expansion_item_index, # 如果是展开的，记录其序号
                                "operation_type": op_type,
                                "table_name": op_table,
                                "success": True,
                                "affected_rows": _affected_rows,
                                "last_insert_id": _last_insert_id if op_type == "insert" else None,
                            },
                            "returned_data": _current_op_result # 可能是 dict 或 list of dicts
                        }
                    # --- END _execute_single_op ---

                    # --- 根据依赖类型执行 --- 
                    if execute_this_op: # 执行单个原始操作（无多行依赖或无依赖）
                        result_data = _execute_single_op(op, index, cursor, schema_cache)
                        batch_results.append(result_data["step_result"]) 
                        if result_data["returned_data"] is not None: # 存入缓存
                            operation_results_cache[index] = result_data["returned_data"]
                    elif dependent_result_list is not None: # 展开执行
                        temp_results_for_cache = []
                        for item_idx, item_res in enumerate(dependent_result_list):
                            op_copy = copy.deepcopy(op) # 为每次展开创建副本
                            # 解析占位符 (使用当前 item_res)
                            op_copy['values'] = replace_placeholders_recursive(op_copy.get('values'), item_res, index) if op_copy.get('operation') == 'insert' else op_copy.get('values')
                            if op_copy.get('operation') == 'update':
                                op_copy['set'] = replace_placeholders_recursive(op_copy.get('set'), item_res, index)
                                op_copy['where'] = replace_placeholders_recursive(op_copy.get('where'), item_res, index)
                            elif op_copy.get('operation') == 'delete':
                                op_copy['where'] = replace_placeholders_recursive(op_copy.get('where'), item_res, index)
                            app.logger.debug(f"Op {index} (Expanded {item_idx+1}): Executing with resolved data {op_copy}")
                            
                            # 执行展开后的单个操作
                            expanded_result = _execute_single_op(op_copy, index, cursor, schema_cache, is_expanded=True, expansion_item_index=item_idx)
                            expanded_op_results.append(expanded_result["step_result"]) # 收集每一步的结果
                            # 如果展开的操作有返回数据，收集起来（这里简单合并，实际可能需要更复杂逻辑）
                            if expanded_result["returned_data"] is not None:
                                temp_results_for_cache.append(expanded_result["returned_data"]) 
                        
                        batch_results.extend(expanded_op_results) # 将所有展开步骤的结果加入主结果列表
                        # 如果收集了多个返回结果，存入缓存 (可能是列表的列表或扁平化列表)
                        if temp_results_for_cache: 
                            # 如果每个展开步骤都返回字典，我们得到列表
                            # 如果某个展开步骤返回列表（不太可能），会是嵌套列表
                            # 简化：假设每个展开步骤最多返回一个 dict
                            operation_results_cache[index] = temp_results_for_cache 
            
            connection.commit()
            app.logger.info("Batch operations completed successfully and transaction committed.")
            return jsonify({"message": "Batch operations executed successfully.", "results": batch_results}), 200
        
        # --- 异常处理 (保持之前的通用化 IntegrityError 处理) ---
        except (ValueError, pymysql.MySQLError, KeyError, IndexError) as e: 
            connection.rollback() 
            current_op_idx = locals().get('current_op_index_for_error', locals().get('index', 'unknown'))
            if isinstance(e, pymysql.err.IntegrityError) and e.args[0] == 1062: 
                error_msg_str = e.args[1]; conflicting_value = "unknown"; key_name_from_db = "unknown"
                match = re.search(r"Duplicate entry '(?P<value>.*?)' for key '(?P<key>.*?)'", error_msg_str)
                if match: conflicting_value = match.group('value'); key_name_from_db = match.group('key')
                else: 
                    match_simple = re.search(r"Duplicate entry '(?P<value>.*?)'", error_msg_str)
                    if match_simple: conflicting_value = match_simple.group('value')
                failed_op_table_name = "unknown"
                if isinstance(current_op_idx, int) and current_op_idx < len(operations):
                    failed_op_table_name = operations[current_op_idx].get('table_name', 'unknown')
                error_detail = {
                    "type": "IntegrityError.DuplicateEntry", 
                    "failed_operation_index": current_op_idx,
                    "table_name": failed_op_table_name,
                    "key_name": key_name_from_db, 
                    "conflicting_value": conflicting_value,
                    "message": (
                        f"Operation at index {current_op_idx} on table '{failed_op_table_name}' "
                        f"failed due to a unique constraint violation. Key: '{key_name_from_db}', Value: '{conflicting_value}'."
                    ),
                    "original_error": error_msg_str
                }
                app.logger.error(
                    f"IntegrityError (DuplicateEntry) at operation {current_op_idx} ... Original DB error: {error_msg_str}",
                    exc_info=False 
                )
                return jsonify({
                    "error": "Unique constraint violation during batch operation.", 
                    "detail": error_detail,
                    "results": batch_results
                }), 409 
            error_msg = f"Error processing batch operation at index {current_op_idx}: {str(e)}"
            app.logger.error(error_msg, exc_info=True) 
            return jsonify({"error": error_msg, "results": batch_results}), 500 
        except Exception as e: 
             connection.rollback()
             current_op_idx = locals().get('current_op_index_for_error', locals().get('index', 'unknown'))
             error_msg = f"Unexpected error during batch operation at index {current_op_idx}: {str(e)}"
             app.logger.error(error_msg, exc_info=True)
             return jsonify({"error": error_msg, "results": batch_results}), 500

if __name__ == '__main__':
    # 注意：从环境变量加载配置或使用默认值
    flask_host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    flask_port = int(os.environ.get('FLASK_RUN_PORT', 5003))
    app.run(host=flask_host, port=flask_port, debug=True)