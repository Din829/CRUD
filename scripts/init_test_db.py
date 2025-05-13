import sqlite3
import csv
import os
import json # 导入 json 库用于读取 schema 文件

# === CI/CD 数据库初始化脚本 ===
# 作用: 该脚本在 GitHub Actions CI 工作流程中运行，
# 用于创建一个临时的 SQLite 测试数据库，并根据项目的 Schema 定义和 CSV 测试数据进行初始化。
# 目的是为后端 API 的单元测试提供一个干净、一致的数据库环境。

# --- 配置 ---
print("--- 配置加载 ---")
# 从环境变量获取测试数据库文件的路径，如果环境变量未设置，则使用默认路径
# 在 .github/workflows/ci_unit_tests.yml 中设置了 TEST_DATABASE_URL
DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test_db_data/test_app.db")
DB_FILE = ""
if DATABASE_URL.startswith("sqlite:///"):
    DB_FILE = DATABASE_URL[len("sqlite:///"):] # 提取 SQLite 文件路径
else:
    print(f"警告: DATABASE_URL 格式非预期 \'{DATABASE_URL}\'. 使用默认数据库路径.")
    DB_FILE = "./test_db_data/test_app.db"
print(f"测试数据库文件路径: {DB_FILE}")

# 定义项目根目录和包含 CSV 及 Schema 文件的目录路径
# __file__ 是当前脚本 (init_test_db.py) 的路径
# os.path.dirname(__file__) 获取脚本所在目录 (scripts)
# os.path.dirname(...) 再次调用获取上级目录 (项目根目录)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
text_dir = os.path.join(base_dir, 'text') # 测试数据和 Schema 文件所在目录
SCHEMA_FILE = os.path.join(text_dir, '表结构.txt') # Schema 定义文件路径
CSV_FILES = { # 定义需要加载的 CSV 文件及其对应的表名
    "users": "users.csv",
    "prompts": "prompts.csv",
    "api_tokens": "api_tokens.csv"
}
print(f"项目根目录: {base_dir}")
print(f"数据/Schema 目录: {text_dir}")
print(f"Schema 文件: {SCHEMA_FILE}")

# --- 辅助函数 ---

def map_mysql_to_sqlite_type(mysql_type):
    """将 MySQL 数据类型映射为 SQLite 兼容的数据类型。
    因为项目主应用使用 MySQL，而 CI 测试使用 SQLite，需要进行类型转换。
    """
    mysql_type_low = mysql_type.lower()
    if "bigint" in mysql_type_low or "int" in mysql_type_low or "tinyint" in mysql_type_low:
        return "INTEGER"
    elif "varchar" in mysql_type_low or "text" in mysql_type_low:
        return "TEXT"
    elif "datetime" in mysql_type_low or "timestamp" in mysql_type_low or "date" in mysql_type_low:
        # 在 SQLite 中将日期/时间存储为 ISO 格式的 TEXT 通常更可靠且兼容性好
        return "TEXT"
    elif "decimal" in mysql_type_low or "float" in mysql_type_low or "double" in mysql_type_low:
        return "REAL" # SQLite 中的浮点数类型
    else:
        # 对于未能识别的 MySQL 类型，打印警告并默认为 TEXT
        print(f"警告: 未映射的 MySQL 类型 \'{mysql_type}\'. 默认映射为 TEXT.")
        return "TEXT"

def create_tables_from_schema(cursor, schema_data):
    """根据从 Schema 文件读取的字典，在 SQLite 数据库中创建表结构。"""
    print("--- 创建数据库表 ---")
    # 定义表创建顺序，优先创建无依赖或被依赖的表 (如 users)
    table_order = ["users", "prompts", "api_tokens"]

    for table_name in table_order:
        if table_name not in schema_data:
            print(f"警告: Schema 文件中未找到表 '{table_name}' 的定义. 跳过.")
            continue
        
        table_info = schema_data[table_name]
        fields = table_info.get("fields", {})
        if not fields:
            print(f"警告: 表 '{table_name}' 在 Schema 中未定义字段. 跳过.")
            continue

        columns_definitions = [] # 存储每个列的定义字符串
        primary_keys_list = []   # 存储声明为 PRIMARY KEY 的列名
        unique_constraints_list = [] # 存储 UNIQUE 约束

        # 遍历 Schema 中定义的每个字段
        for field_name, details in fields.items():
            sqlite_type = map_mysql_to_sqlite_type(details.get("type", "TEXT"))
            col_def = f'"{field_name}" {sqlite_type}' # 列名用双引号包裹以处理特殊字符
            
            if details.get("null", "YES").upper() == "NO":
                col_def += " NOT NULL"
            if details.get("key", "").upper() == "PRI":
                primary_keys_list.append(f'"{field_name}"')
            if details.get("key", "").upper() == "UNI":
                # 为每个声明为 UNIQUE 的列创建一个单独的 UNIQUE 约束
                unique_constraints_list.append(f'UNIQUE ("{field_name}")')
            
            # 注意: SQLite 对 DEFAULT CURRENT_TIMESTAMP 的直接支持可能因版本而异
            # 在测试脚本中，通常依赖应用程序逻辑或在插入时显式处理时间戳
            columns_definitions.append(col_def)

        # 添加主键约束
        if primary_keys_list:
            # 检查是否是标准的单一 'id' 主键，并且是整数类型，以便设为 AUTOINCREMENT
            is_standard_id_pk = len(primary_keys_list) == 1 and primary_keys_list[0] == '"id"'
            id_field_info = fields.get("id", {}) # 获取 id 字段的详细信息
            
            # 启发式：如果主键是名为 'id' 的单个整数列，则假定其为自增主键
            if is_standard_id_pk and "int" in id_field_info.get("type", "").lower():
                # 在列定义中直接声明 PRIMARY KEY AUTOINCREMENT
                for i, col_def_str in enumerate(columns_definitions):
                    if col_def_str.startswith('"id" INTEGER'): # 定位到 id 列的定义
                        columns_definitions[i] += " PRIMARY KEY AUTOINCREMENT"
                        primary_keys_list = [] # 因为已在列定义中处理，清空单独的主键列表
                        break
            else: # 如果不是标准的自增 id，或者存在复合主键
                columns_definitions.append(f"PRIMARY KEY ({', '.join(primary_keys_list)})")

        # 添加所有 UNIQUE 约束
        columns_definitions.extend(unique_constraints_list)

        # 手动添加外键约束 (因为 表结构.txt 中 foreign_keys 为空)
        # 这些是基于项目常见实践和 CSV 文件推断的
        if table_name == "prompts":
            columns_definitions.append("FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE")
        elif table_name == "api_tokens":
            columns_definitions.append("FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE")
            
        # 构建并执行 CREATE TABLE 语句
        # 使用单引号作为f-string的外部引号，避免与表名/列名的双引号冲突
        create_table_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(columns_definitions)});'
        try:
            print(f"执行 SQL: {create_table_sql}")
            cursor.execute(create_table_sql)
        except sqlite3.Error as e:
            print(f"创建表 {table_name} 时发生错误: {e}")
            print(f"出错的 SQL: {create_table_sql}")
             
    print("--- 数据库表创建阶段完成 ---")

def load_csv_data(cursor, table_name, csv_filename, schema_fields_dict):
    """从指定的 CSV 文件加载数据到数据库表中。"""
    csv_path = os.path.join(text_dir, csv_filename)
    if not os.path.exists(csv_path):
        print(f"警告: CSV 文件未找到于 {csv_path}. 跳过表 {table_name} 的数据加载.")
        return
    
    print(f"--- 从 {csv_filename} 为表 {table_name} 加载数据 ---")
    inserted_count = 0
    skipped_count = 0
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8-sig') as f: # utf-8-sig 处理 BOM
            reader = csv.DictReader(f) # 使用 DictReader可以直接通过列名获取值
            
            csv_headers = reader.fieldnames
            if not csv_headers:
                print(f"警告: CSV 文件 {csv_filename} 为空或没有表头. 跳过.")
                return

            # 从 Schema 中获取当前表实际存在的列名，并与 CSV 表头进行匹配
            # 只插入那些在 CSV 和数据库表 Schema 中都存在的列
            db_cols_to_insert = [col for col in schema_fields_dict.keys() if col in csv_headers]
            
            if not db_cols_to_insert:
                print(f"警告: 对于表 {table_name}，CSV 表头 {csv_headers} 与 Schema 字段 {list(schema_fields_dict.keys())} 无匹配列. 跳过.")
                return
                 
            placeholders = ', '.join(['?'] * len(db_cols_to_insert)) # 生成对应列数的占位符
            # 构建带引号的列名列表字符串
            formatted_columns = ", ".join([f'"{c}"' for c in db_cols_to_insert])
            # 使用单引号作为f-string的外部引号，并插入格式化好的列名
            sql = f'INSERT INTO "{table_name}" ({formatted_columns}) VALUES ({placeholders})'
            # print(f"准备的 INSERT 语句: {sql}") # 用于调试

            for row_number, row_data in enumerate(reader, 1):
                values_to_insert = []
                try:
                    for db_col_name in db_cols_to_insert:
                        values_to_insert.append(row_data.get(db_col_name))
                    
                    # print(f"执行 SQL: {sql} 参数: {tuple(values_to_insert)}") # 用于调试
                    cursor.execute(sql, tuple(values_to_insert))
                    inserted_count += 1
                except sqlite3.IntegrityError as ie:
                    # 例如 UNIQUE 约束冲突
                    # print(f"跳过行 {row_number} (表 {table_name}) 由于数据完整性错误: {ie} - 数据: {row_data}")
                    skipped_count += 1
                except sqlite3.Error as db_err:
                    print(f"跳过行 {row_number} (表 {table_name}) 由于数据库错误: {db_err} - 数据: {row_data} - SQL: {sql}")
                    skipped_count += 1
                        
        print(f"表 {table_name} 数据加载完成. 插入: {inserted_count} 行, 跳过: {skipped_count} 行.")
    except Exception as e:
        print(f"从 {csv_filename} 向表 {table_name} 加载数据时发生意外错误: {e}")

# --- 主执行逻辑 ---
conn = None # 初始化数据库连接对象
try:
    # 1. 读取 Schema 配置文件
    if not os.path.exists(SCHEMA_FILE):
        raise FileNotFoundError(f"Schema 配置文件未找到: {SCHEMA_FILE}")
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        schema_config_data = json.load(f) # 解析 JSON格式的 Schema 定义

    # 2. 确保测试数据库文件所在的目录存在
    db_dir = os.path.dirname(DB_FILE)
    if db_dir and not os.path.exists(db_dir): # 只有当 DB_FILE 包含目录路径时才创建
        os.makedirs(db_dir)
        print(f"创建目录: {db_dir}")


    # 3. 连接到 SQLite 数据库 (如果文件不存在则自动创建)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;") # 为 SQLite 开启外键约束支持
    print(f"--- 开始初始化测试数据库于 {DB_FILE} ---")

    # 4. 根据 Schema 创建表
    create_tables_from_schema(cursor, schema_config_data)

    # 5. 从 CSV 文件加载初始数据 (按依赖顺序加载：先 users)
    if "users" in schema_config_data and "users" in CSV_FILES:
        load_csv_data(cursor, "users", CSV_FILES["users"], schema_config_data["users"].get("fields", {}))
    
    # 确保 prompts 表的 user_id 能正确关联 users 表的 id
    if "prompts" in schema_config_data and "prompts" in CSV_FILES:
        load_csv_data(cursor, "prompts", CSV_FILES["prompts"], schema_config_data["prompts"].get("fields", {}))
        
    # 确保 api_tokens 表的 user_id 能正确关联 users 表的 id
    if "api_tokens" in schema_config_data and "api_tokens" in CSV_FILES:
        load_csv_data(cursor, "api_tokens", CSV_FILES["api_tokens"], schema_config_data["api_tokens"].get("fields", {}))

    # 6. 提交所有数据库更改
    conn.commit()
    print("--- 测试数据库初始化成功 ---")

except FileNotFoundError as e:
    print(f"错误: 必需文件未找到: {e}")
except json.JSONDecodeError as e:
    print(f"错误: 解析 Schema 文件 '{SCHEMA_FILE}' 失败: {e}")
except sqlite3.Error as e:
    print(f"SQLite 数据库操作错误: {e}")
    if conn:
        conn.rollback() # 如果发生错误，回滚事务
except Exception as e:
    # 捕获所有其他类型的未知错误
    print(f"初始化测试数据库过程中发生意外错误: {e}")
    if conn:
        conn.rollback()
finally:
    # 确保数据库连接在脚本结束时总是关闭
    if conn:
        conn.close()
        print("数据库连接已关闭.")
