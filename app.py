from flask import Flask, request, jsonify
import pymysql
import logging
import os
from datetime import datetime
from contextlib import contextmanager
import locale  # 新增：支持英文日期解析
import json
from decimal import Decimal # 新增 Decimal 导入

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# 数据库连接上下文管理器
@contextmanager
def get_db_connection():
    connection = pymysql.connect(
        host=os.environ.get('DB_HOST', '192.168.0.32'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', 'q75946123'),
        database=os.environ.get('DB_NAME', 'sky_take_out'),
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

    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = [{"table_name": data.get("table_name"), "fields": data.get("fields", [])}]
    else:
        return jsonify({"error": "Request body must be a list or dict"}), 400

    if not records:
        return jsonify({"error": "No records provided"}), 400

    with get_db_connection() as connection:
        try:
            with connection.cursor() as cursor:
                results = []
                inserted_ids = {}  # 记录主表插入结果，如 {"<new_setmeal_id>": 50}

                for record in records:
                    if isinstance(record, str):
                        try:
                            record = json.loads(record)
                        except json.JSONDecodeError as e:
                            raise ValueError(f"Invalid record format: {str(e)}")
                    
                    table_name = record.get("table_name")
                    fields_list = record.get("fields", [])
                    
                    if not table_name or not fields_list:
                        raise ValueError(f"Missing table_name or fields for {table_name}")
                    if not isinstance(fields_list, list):
                        fields_list = [fields_list]

                    cursor.execute(f"DESCRIBE {table_name}")
                    schema = {row["Field"]: {
                        "type": row["Type"].lower(),
                        "null": row["Null"],
                        "key": row["Key"],
                        "default": row["Default"]
                    } for row in cursor.fetchall()}
                    app.logger.debug(f"Schema for {table_name}: {schema}")

                    primary_key = next((f for f, v in schema.items() if v["key"] == "PRI"), None)
                    if not primary_key:
                        raise ValueError(f"No primary key found for table {table_name}")

                    for fields in fields_list:
                        # 替换主键占位符，如 <new_setmeal_id>
                        for k, v in fields.items():
                            if isinstance(v, str) and v.startswith("<new_") and v.endswith("_id>"):
                                if v in inserted_ids:
                                    fields[k] = inserted_ids[v]
                                else:
                                    raise ValueError(f"占位符 {v} 未定义，主表可能尚未插入")

                        # 仅检查无默认值的 NOT NULL 字段
                        required_fields = {f for f, v in schema.items() if v["null"] == "NO" and v["key"] != "PRI" and v["default"] is None}
                        missing = required_fields - set(fields.keys())
                        if missing:
                            raise ValueError(f"Missing required fields {missing} for {table_name}")

                        # 自动生成主键值（字符串型）
                        if primary_key not in fields and "int" not in schema[primary_key]["type"]:
                            cursor.execute(f"SELECT MAX({primary_key}) FROM {table_name}")
                            max_id = cursor.fetchone()[f"MAX({primary_key})"]
                            if max_id:
                                prefix = ''.join(c for c in max_id if not c.isdigit())
                                num = int(''.join(c for c in max_id if c.isdigit())) + 1
                                length = len(max_id) - len(prefix)
                                fields[primary_key] = f"{prefix}{num:0{length}d}"
                            else:
                                fields[primary_key] = "REP000001"

                        # 日期和 NOW() 处理
                        date_types = ["datetime", "timestamp", "date"]
                        params = []
                        columns = []
                        for field, value in fields.items():
                            field_type = schema[field]["type"]
                            if any(dt in field_type for dt in date_types) and value:
                                if isinstance(value, str) and value.lower() == "now()":
                                    columns.append(field)
                                    params.append("NOW()")  # 直接使用 MySQL NOW() 函数
                                else:
                                    columns.append(field)
                                    params.append(parse_date(str(value).strip(), field_type))
                            else:
                                columns.append(field)
                                params.append(value)

                        sql_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s' if p != 'NOW()' else p for p in params])})"
                        app.logger.debug(f"Executing SQL: {sql_query} with values: {params}")
                        cursor.execute(sql_query, [p for p in params if p != "NOW()"])

                        # 记录新插入的主键值
                        cursor.execute(f"SELECT LAST_INSERT_ID()")
                        inserted_id = cursor.fetchone()['LAST_INSERT_ID()']
                        inserted_ids[f"<new_{table_name}_id>"] = inserted_id

                        results.append(f"Record inserted into {table_name}: {primary_key}={inserted_id}")

                connection.commit()
                app.logger.debug(f"Inserted records: {results}")
                return jsonify({
                    "message": "\n".join(results),
                    "inserted_records": [record["fields"] for record in records]
                })

        except Exception as e:
            connection.rollback()
            app.logger.error(f"Error inserting records: {str(e)}")
            return jsonify({"error": str(e)}), 500


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