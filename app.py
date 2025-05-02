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

app = Flask(__name__)
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
    app.logger.debug(f"Received SQL query: {sql_query}")

    if not sql_query:
        return jsonify({"error": "No SQL query provided"}), 400

    if not sql_query.strip().upper().startswith('SELECT'):
        return jsonify({"error": "Only SELECT queries are allowed"}), 403

    with get_db_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                result = cursor.fetchall()
                app.logger.debug(f"Query result: {result}")
                return jsonify(result)
        except Exception as e:
            app.logger.error(f"Error executing query: {str(e)}")
            return jsonify({"error": str(e)}), 500





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
    with get_db_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = [row[f"Tables_in_{connection.db.decode()}"] for row in cursor.fetchall()]
                schema = {}
                for table in tables:
                    cursor.execute(f"DESCRIBE {table}")
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
                app.logger.debug(f"Schema retrieved: {schema}")
                return jsonify({"result": [json.dumps(schema, ensure_ascii=False)]})
        except Exception as e:
            app.logger.error(f"Error fetching schema: {str(e)}")
            return jsonify({"error": str(e)}), 500



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
                
                # 返回结果，原有逻辑不变
                if affected_rows > 0:
                    app.logger.debug(f"Deleted record in {table_name}: {primary_key}={primary_value}")
                    return jsonify({"message": f"Record with {primary_key}={primary_value} deleted successfully"})
                else:
                    return jsonify({"error": f"No record found with {primary_key}={primary_value} in {table_name}"}), 404

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)