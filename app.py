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

    # 用于存储先前操作返回的结果，供后续依赖使用 (索引 -> 结果字典)
    operation_results_cache = {} 
    # 存储每个操作的执行结果
    batch_results = [] 
    # === 新增：初始化 Schema 缓存字典 ===
    schema_cache = {}

    with get_db_connection() as connection:
        try:
            connection.begin() # 开始事务
            with connection.cursor() as cursor:
                for index, op in enumerate(operations):
                    app.logger.info(f"Processing operation {index}: {op}")
                    operation_type = op.get("operation", "").lower()
                    table_name = op.get("table_name")

                    if not table_name:
                        raise ValueError(f"Operation {index}: Missing 'table_name'.")

                    # --- 依赖处理: 替换占位符 ---
                    # (修改：现在也处理 where_dict 中的占位符)
                    depends_on_index = op.get("depends_on_index")
                    if depends_on_index is not None:
                        if not isinstance(depends_on_index, int) or depends_on_index < 0 or depends_on_index >= index:
                            raise ValueError(f"Operation {index}: Invalid 'depends_on_index' value: {depends_on_index}.")
                        
                        dependent_result = operation_results_cache.get(depends_on_index)
                        if dependent_result is None:
                            raise ValueError(f"Operation {index}: Could not find result for dependency index {depends_on_index}.")

                        # --- 函数：递归替换字典/列表中的占位符 ---
                        def replace_placeholders_recursive(item, dep_result):
                            if isinstance(item, dict):
                                return {k: replace_placeholders_recursive(v, dep_result) for k, v in item.items()}
                            elif isinstance(item, list):
                                return [replace_placeholders_recursive(elem, dep_result) for elem in item]
                            elif isinstance(item, str):
                                match = re.match(r"\{\{previous_result\[(\d+)\]\.(\w+)\}\}", item)
                                if match:
                                    dep_idx_str, field_name = match.groups()
                                    dep_idx = int(dep_idx_str)
                                    if dep_idx == depends_on_index: # 确保索引匹配
                                        if field_name in dep_result:
                                             replaced_value = dep_result[field_name]
                                             app.logger.info(f"Op {index}: Replaced placeholder '{item}' with value '{replaced_value}' from op {depends_on_index}")
                                             return replaced_value
                                        else:
                                            raise ValueError(f"Op {index}: Placeholder field '{field_name}' not found in result of dependency index {depends_on_index}.")
                                    else:
                                        raise ValueError(f"Op {index}: Placeholder index {dep_idx} does not match depends_on_index {depends_on_index}.")
                                return item # 没有匹配，返回原字符串
                            else:
                                return item # 其他类型，直接返回
                        # --- END 函数定义 ---

                        # 在需要的地方（values, set, where）替换占位符
                        if operation_type == "insert" and "values" in op:
                             op["values"] = replace_placeholders_recursive(op["values"], dependent_result)
                             app.logger.debug(f"Op {index}: Values after potential replacement: {op['values']}")
                        elif operation_type == "update":
                             if "set" in op:
                                 op["set"] = replace_placeholders_recursive(op["set"], dependent_result)
                                 app.logger.debug(f"Op {index}: Set after potential replacement: {op['set']}")
                             if "where" in op:
                                 op["where"] = replace_placeholders_recursive(op["where"], dependent_result)
                                 app.logger.debug(f"Op {index}: Where after potential replacement: {op['where']}")
                        elif operation_type == "delete" and "where" in op:
                             op["where"] = replace_placeholders_recursive(op["where"], dependent_result)
                             app.logger.debug(f"Op {index}: Where after potential replacement: {op['where']}")

                    # --- 根据操作类型构建和执行 SQL ---
                    current_op_result_data = {} # 用于存储此操作需要返回的数据
                    affected_rows = 0

                    # --- 预先获取当前操作表的 Schema --- 
                    table_schema = schema_cache.get(table_name)
                    if not table_schema:
                        # 尝试从数据库加载（理论上应该在入口处已缓存，作为后备）
                        try:
                             cursor.execute(f"DESCRIBE `{table_name}`")
                             table_schema = {row["Field"]: {
                                 "type": row["Type"].lower(), "null": row["Null"],
                                 "key": row["Key"], "default": row["Default"],
                                 "extra": row.get("Extra", "")
                             } for row in cursor.fetchall()}
                             schema_cache[table_name] = table_schema # 存入缓存
                        except Exception as schema_e:
                             raise ValueError(f"Operation {index}: Failed to get schema for table '{table_name}': {schema_e}")

                    # --- 函数：准备参数值（类型转换等） ---
                    def prepare_param_value(column_name, value, current_cursor):
                        # --- 原有的类型转换逻辑 (占位符已在 LangGraph 层处理) ---
                        if column_name not in table_schema:
                            app.logger.warning(f"Op {index}: Column '{column_name}' not found in schema for table '{table_name}', skipping type conversion.")
                            return value # 如果列不在 schema 中，返回当前值

                        col_info = table_schema[column_name]
                        col_type = col_info["type"].lower()
                        date_types = ["datetime", "timestamp", "date"]
                        numeric_types = ["int", "tinyint", "bigint", "decimal", "float"]

                        # 1. 处理日期时间类型
                        if any(dt in col_type for dt in date_types):
                            if isinstance(value, str) and value:
                                try:
                                    parsed_dt = parse_date(value.strip(), col_type)
                                    app.logger.debug(f"Op {index}: Parsed date for column '{column_name}': '{value}' -> '{parsed_dt}' (type: {type(parsed_dt)})" )
                                    return parsed_dt
                                except ValueError as date_e:
                                    raise ValueError(f"Op {index}: Invalid date format for column '{column_name}': '{value}' - {date_e}")
                            elif isinstance(value, datetime):
                                return value
                            elif value is None and col_info.get('null') == 'YES':
                                return None
                            else:
                                raise ValueError(f"Op {index}: Invalid type or null value for date column '{column_name}': {type(value)}")

                        # 2. 处理数字类型
                        elif any(nt in col_type for nt in numeric_types):
                            if isinstance(value, str) and value:
                                 try:
                                      if "int" in col_type or "bigint" in col_type or "tinyint" in col_type:
                                           return int(value)
                                      else: # float, decimal
                                           return float(value)
                                 except ValueError:
                                      raise ValueError(f"Op {index}: Invalid numeric value for column '{column_name}' after processing: '{value}'")
                            elif isinstance(value, (int, float, Decimal)):
                                return value
                            elif value is None and col_info.get('null') == 'YES':
                                return None
                            else:
                                raise ValueError(f"Op {index}: Invalid type or null value for numeric column '{column_name}': {type(value)}")

                        # 3. 其他情况返回当前值
                        return value
                    # --- END 函数定义 ---

                    if operation_type == "insert":
                        values_dict = op.get("values")
                        if not isinstance(values_dict, dict):
                            raise ValueError(f"Operation {index} (insert): 'values' must be a dictionary.")
                        
                        columns = []
                        value_placeholders = []
                        params = []
                        for col, val in values_dict.items():
                             columns.append(f"`{col}`") 
                             if isinstance(val, str) and val.lower() == "now()":
                                 value_placeholders.append("NOW()")
                             else:
                                 value_placeholders.append("%s")
                                 # 在添加参数前进行准备/转换
                                 prepared_val = prepare_param_value(col, val, cursor)
                                 params.append(prepared_val)
                        
                        cols_str = ", ".join(columns)
                        vals_str = ", ".join(value_placeholders)
                        sql = f"INSERT INTO `{table_name}` ({cols_str}) VALUES ({vals_str})"
                        app.logger.debug(f"Op {index}: Executing SQL: {sql} with params: {params}")
                        cursor.execute(sql, params)
                        affected_rows = cursor.rowcount
                        last_insert_id = cursor.lastrowid

                        # 处理 return_affected (仅限 INSERT)
                        return_fields = op.get("return_affected")
                        if last_insert_id and isinstance(return_fields, list) and return_fields:
                            # 需要获取刚插入记录的主键名 (这里假设它是 'id'，实际应从 Schema 获取)
                            # TODO: 获取主键名，而不是硬编码 'id'
                            pk_name = "id" 
                            query_cols_str = ", ".join([f"`{f}`" for f in return_fields])
                            fetch_sql = f"SELECT {query_cols_str} FROM `{table_name}` WHERE `{pk_name}` = %s"
                            cursor.execute(fetch_sql, [last_insert_id])
                            fetched_result = cursor.fetchone()
                            if fetched_result:
                                current_op_result_data = fetched_result
                                app.logger.info(f"Op {index}: Fetched affected fields: {current_op_result_data}")
                            else:
                                app.logger.warning(f"Op {index}: Could not fetch affected fields for inserted ID {last_insert_id}")

                    elif operation_type == "update":
                        where_dict = op.get("where")
                        set_dict = op.get("set")
                        if not isinstance(where_dict, dict) or not where_dict:
                            raise ValueError(f"Operation {index} (update): 'where' clause dictionary cannot be empty.")
                        if not isinstance(set_dict, dict) or not set_dict:
                            raise ValueError(f"Operation {index} (update): 'set' clause dictionary cannot be empty.")

                        set_parts = []
                        params = [] 
                        
                        # --- 修改 SET 子句处理逻辑 (对齐其他端点) --- 
                        for col, val in set_dict.items():
                            # 1. 显式检查 NOW()
                            if isinstance(val, str) and val.lower() == "now()":
                                set_parts.append(f"`{col}` = NOW()")
                            # 2. 其他所有值都参数化处理
                            else:
                                set_parts.append(f"`{col}` = %s")
                                prepared_val = prepare_param_value(col, val, cursor) # 复用之前的类型准备函数
                                params.append(prepared_val)
                        # --- END 修改 SET 子句处理逻辑 ---
                        
                        where_parts = []
                        # WHERE 子句处理逻辑
                        for col, condition in where_dict.items():
                            if isinstance(condition, dict):
                                # 处理字典形式的条件，如 {"like": ...}, {"in": ...}
                                op_key = next(iter(condition)).lower()
                                op_val = condition[op_key]
                                if op_key == 'like':
                                    where_parts.append(f"`{col}` LIKE %s")
                                    params.append(op_val) # LIKE 的值是字符串，直接添加参数
                                elif op_key == 'in':
                                    # 检查 op_val 是否是列表/元组或子查询字符串
                                    if isinstance(op_val, (list, tuple)):
                                        if not op_val: # IN 一个空列表会报错
                                             raise ValueError(f"Operation {index}: 'IN' operator value for column '{col}' cannot be an empty list/tuple.")
                                        # 构建占位符字符串，例如 "(%s, %s, %s)"
                                        placeholders = ", ".join(["%s"] * len(op_val))
                                        where_parts.append(f"`{col}` IN ({placeholders})")
                                        params.extend(op_val) # 将列表中的所有值添加到参数
                                    elif isinstance(op_val, str) and op_val.strip().startswith("(") and op_val.strip().endswith(")"):
                                        # === START FIX for MySQL 1093 Error ===
                                        subquery = op_val.strip()
                                        # 简单的检查，看子查询是否包含 "FROM `table_name`" 或 "FROM table_name"
                                        # 注意：这可能不够鲁棒，例如表名出现在注释或字符串字面量中。更严格的解析会更好，但这里先用简单方法。
                                        # 我们需要检查 `table_name` 被反引号包围和不被包围两种情况
                                        target_table_pattern_1 = f"FROM `{table_name}`"
                                        target_table_pattern_2 = f"FROM {table_name}" # 可能没有反引号
                                        # 使用小写比较来增加匹配机会
                                        if target_table_pattern_1.lower() in subquery.lower() or target_table_pattern_2.lower() in subquery.lower():
                                            app.logger.warning(f"Op {index}: Wrapping subquery for column '{col}' to avoid MySQL 1093 error.")
                                            # 使用别名确保唯一性，以防一个 WHERE 中有多个此类子查询
                                            wrapped_subquery = f"(SELECT * FROM {subquery} AS temp_subquery_{col}_{index})" 
                                            where_parts.append(f"`{col}` IN {wrapped_subquery}")
                                        else:
                                            # 子查询不引用目标表，或者我们的检查不够智能，按原样拼接
                                            app.logger.warning(f"Op {index}: Directly embedding subquery in WHERE clause for column '{col}': {subquery}")
                                            where_parts.append(f"`{col}` IN {subquery}") # 直接拼接子查询
                                        # === END FIX for MySQL 1093 Error ===
                                    else:
                                        raise ValueError(f"Operation {index}: Unsupported value type for 'IN' operator in WHERE clause for column '{col}': {type(op_val)}. Expected list/tuple or subquery string.")
                                else:
                                     raise ValueError(f"Operation {index}: Unsupported dictionary operator '{op_key}' in WHERE clause for column '{col}'.")
                            else:
                                # 处理简单的等于条件
                                where_parts.append(f"`{col}` = %s")
                                prepared_condition = prepare_param_value(col, condition, cursor)
                                params.append(prepared_condition)

                        set_clause = ", ".join(set_parts)
                        where_clause = " AND ".join(where_parts)
                        sql = f"UPDATE `{table_name}` SET {set_clause} WHERE {where_clause}"
                        app.logger.debug(f"Op {index}: Executing SQL: {sql} with params: {params}")
                        cursor.execute(sql, params)
                        affected_rows = cursor.rowcount
                        
                        # --- 新增：处理 UPDATE 的 return_affected --- 
                        return_fields = op.get("return_affected")
                        if affected_rows > 0 and isinstance(return_fields, list) and return_fields:
                            # 重新查询以获取被更新记录的指定字段
                            # 注意：这假设 WHERE 条件足够精确以定位记录。
                            # 如果 UPDATE 可能影响多行，这里只获取第一个匹配行的结果。
                            query_cols_str = ", ".join([f"`{f}`" for f in return_fields])
                            # 使用与 UPDATE 相同的 WHERE 条件和参数来查询
                            # 需要从完整的 params 列表中分离出 WHERE 子句对应的参数
                            where_params = params[len(set_parts):] # 假设 WHERE 参数在 SET 参数之后
                            fetch_sql = f"SELECT {query_cols_str} FROM `{table_name}` WHERE {where_clause}"
                            app.logger.debug(f"Op {index}: Fetching affected fields after update. SQL: {fetch_sql} with params: {where_params}")
                            cursor.execute(fetch_sql, where_params)
                            fetched_result = cursor.fetchone() # 只获取一行
                            if fetched_result:
                                current_op_result_data = fetched_result
                                app.logger.info(f"Op {index}: Fetched affected fields after update: {current_op_result_data}")
                            else:
                                # 可能因为事务隔离级别或其他原因没查到刚更新的行？或者 WHERE 条件有问题？
                                app.logger.warning(f"Op {index}: Could not fetch affected fields after update using WHERE: {where_clause} with params {where_params}")
                        # --- END 新增 ---

                    elif operation_type == "delete":
                        where_dict = op.get("where")
                        if not isinstance(where_dict, dict) or not where_dict:
                            raise ValueError(f"Operation {index} (delete): 'where' clause dictionary cannot be empty.")
                        
                        where_parts = []
                        params = []
                        for col, condition in where_dict.items():
                            if isinstance(condition, dict):
                                op_key = next(iter(condition)).lower()
                                op_val = condition[op_key]
                                if op_key == 'like':
                                    where_parts.append(f"`{col}` LIKE %s")
                                    params.append(op_val)
                                else:
                                     raise ValueError(f"Operation {index} (delete): Unsupported operator '{op_key}' in WHERE clause for column '{col}'.")
                            else:
                                where_parts.append(f"`{col}` = %s")
                                # 在添加参数前进行准备/转换
                                prepared_condition = prepare_param_value(col, condition, cursor)
                                params.append(prepared_condition)
                        
                        where_clause = " AND ".join(where_parts)
                        sql = f"DELETE FROM `{table_name}` WHERE {where_clause}"
                        app.logger.debug(f"Op {index}: Executing SQL: {sql} with params: {params}")
                        cursor.execute(sql, params)
                        affected_rows = cursor.rowcount

                    else:
                        raise ValueError(f"Operation {index}: Unsupported operation type '{operation_type}'.")

                    # 记录单步操作结果
                    step_result = {
                        "operation_index": index,
                        "operation_type": operation_type,
                        "table_name": table_name,
                        "success": True,
                        "affected_rows": affected_rows,
                    }
                    if operation_type == "insert" and last_insert_id:
                         step_result["last_insert_id"] = last_insert_id
                    batch_results.append(step_result)

                    # 如果此操作需要返回结果给后续步骤，存入缓存
                    if current_op_result_data:
                        operation_results_cache[index] = current_op_result_data

            connection.commit() # 所有操作成功，提交事务
            app.logger.info("Batch operations completed successfully and transaction committed.")
            return jsonify({"message": "Batch operations executed successfully.", "results": batch_results}), 200

        except (ValueError, pymysql.MySQLError, KeyError, IndexError) as e: # 捕获各类可能的错误
            connection.rollback() # 出错，回滚事务
            error_msg = f"Error processing batch operation at index {index if 'index' in locals() else 'unknown'}: {str(e)}"
            app.logger.error(error_msg, exc_info=True) # 记录完整异常信息
            # 在 batch_results 中标记错误发生的位置
            if 'index' in locals():
                 if index < len(batch_results): # 如果错误发生在添加结果之前
                      pass # batch_results 已经是正确的
                 else: # 错误发生在执行 SQL 之后，添加结果之前
                      batch_results.append({
                           "operation_index": index,
                           "success": False,
                           "error": str(e)
                      })
            
            return jsonify({"error": error_msg, "results": batch_results}), 500
        except Exception as e: # 捕获其他意外错误
             connection.rollback()
             error_msg = f"Unexpected error during batch operation: {str(e)}"
             app.logger.error(error_msg, exc_info=True)
             return jsonify({"error": error_msg, "results": batch_results}), 500

if __name__ == '__main__':
    # 注意：从环境变量加载配置或使用默认值
    flask_host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    flask_port = int(os.environ.get('FLASK_RUN_PORT', 5003))
    app.run(host=flask_host, port=flask_port, debug=True)