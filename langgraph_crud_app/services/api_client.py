# api_client.py: 封装了向后端 Flask API 发送 HTTP 请求的逻辑。

import requests
import json
from typing import List, Dict, Any, Optional

# --- 配置 ---
# TODO: 后续将此 URL 移至 config/settings.py 以进行更好的管理
BASE_API_URL = "http://127.0.0.1:5003"  # 修改为本地主机地址，确保与Flask服务在同一台机器上
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 10 # 默认请求超时时间（秒）

# --- API 调用函数 ---

def get_schema() -> List[str]:
    """
    调用 Flask API 端点以检索数据库 Schema。

    对应 Dify 节点 '1742268541036' 的逻辑。

    返回:
        一个包含单个 JSON 字符串的列表，代表 Schema，
        与 Dify 节点的输出格式匹配。
    抛出:
        requests.exceptions.RequestException: 如果 API 请求失败。
        ValueError: 如果响应不是有效的 JSON 或格式不符合预期。
    """
    api_url = f"{BASE_API_URL}/get_schema"
    try:
        response = requests.get(api_url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status() # 对错误的 HTTP 状态码 (4xx 或 5xx) 抛出异常
        data = response.json()
        # Dify 节点期望一个包含 JSON 字符串的列表
        if isinstance(data, dict) and "result" in data and isinstance(data["result"], list):
             # Flask API 在 'result' 键中包装了 schema 字典的列表
             # 我们需要按原样返回这个列表，因为 Dify 节点期望 array[string]
             return data["result"]
        elif isinstance(data, dict): # 如果 API 响应格式改变，处理直接返回字典的情况
             # 将字典包装在列表中的 JSON 字符串中，以匹配 Dify 的期望
             return [json.dumps(data, ensure_ascii=False)]
        else:
            # 如果格式不符合预期，抛出错误
            raise ValueError(f"来自 {api_url} 的响应格式不符合预期: {data}")
    except requests.exceptions.RequestException as e:
        print(f"调用 get_schema API 时出错: {e}")
        raise
    except (json.JSONDecodeError, ValueError) as e:
        print(f"处理 get_schema 响应时出错: {e}")
        raise ValueError(f"来自 {api_url} 的无效响应")


def execute_query(sql_query: str) -> str:
    """
    调用 Flask API 端点以执行 SELECT SQL 查询。

    对应 Dify 节点 '1742268852484' 的逻辑。

    参数:
        sql_query: SQL SELECT 查询字符串。

    返回:
        代表查询结果 (字典列表) 的 JSON 字符串。
    抛出:
        requests.exceptions.RequestException: 如果 API 请求失败。
        ValueError: 如果响应不是有效的 JSON或者SQL存在语法错误。
    """
    api_url = f"{BASE_API_URL}/execute_query"
    
    # 记录原始SQL信息
    sql_length = len(sql_query) if sql_query else 0
    print(f"--- API客户端: 准备执行SQL查询 (长度: {sql_length}) ---")
    if sql_length > 200:
        print(f"SQL前200字符: {sql_query[:200]}...")
        print(f"SQL后200字符: ...{sql_query[-200:]}")
    
    # 前置检查
    if not sql_query or not sql_query.strip():
        print("错误: 空的SQL查询")
        raise ValueError("空的SQL查询")
        
    # 确保SQL是SELECT语句
    if not sql_query.strip().upper().startswith("SELECT"):
        print(f"错误: 非SELECT查询: {sql_query}")
        raise ValueError(f"查询必须以SELECT开头: {sql_query}")
    
    # 清理SQL：移除尾部分号（API会自己处理）
    sql_query = sql_query.strip()
    has_semicolon = sql_query.endswith(';')
    while sql_query.endswith(';'):
        sql_query = sql_query[:-1].strip()
    
    # 再次检查清理后的SQL
    if not sql_query:
        print("错误: 清理后SQL为空")
        raise ValueError("清理后SQL为空")
    
    # 检查是否包含UNION ALL
    if " UNION ALL " in sql_query.upper():
        parts = sql_query.upper().split(" UNION ALL ")
        print(f"检测到SQL包含{len(parts)}个UNION ALL部分")
        for i, part in enumerate(parts):
            if not part.strip().startswith("SELECT"):
                print(f"警告: UNION ALL部分{i+1}不是有效的SELECT语句")
    
    print(f"发送查询到API (长度: {len(sql_query)})...")
    payload = {"sql_query": sql_query}
    
    try:
        response = requests.post(api_url, headers=HEADERS, json=payload, timeout=TIMEOUT)
        
        # 记录API响应，帮助调试
        print(f"API响应状态码: {response.status_code}")
        
        # 如果是错误响应，尝试从响应内容提取有用信息
        if response.status_code != 200:
            try:
                error_data = response.json()
                if isinstance(error_data, dict) and "error" in error_data:
                    error_message = error_data["error"]
                    print(f"API错误详情: {error_message}")
                    # 将API返回的错误消息抛出，保留完整信息
                    raise ValueError(f"API错误: {error_message}")
            except json.JSONDecodeError:
                # 如果无法解析JSON错误响应，使用原始内容
                error_content = response.text[:200] + ("..." if len(response.text) > 200 else "")
                print(f"API返回非JSON错误响应: {error_content}")
        
        # 正常处理响应
        response.raise_for_status()
        result_data = response.json()
        # 检查响应结果
        response_json = json.dumps(result_data, ensure_ascii=False)
        print(f"SQL查询成功，结果长度: {len(response_json)}")
        if len(response_json) > 100:
            print(f"结果预览: {response_json[:100]}...")
        
        return response_json
    
    except requests.exceptions.RequestException as e:
        print(f"调用 execute_query API 时出错: {e}")
        # 检查是否有API返回的错误信息
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                if isinstance(error_data, dict) and "error" in error_data:
                    # 提取API返回的具体错误信息
                    error_detail = error_data['error']
                    # 检查是否是SQL语法错误
                    if isinstance(error_detail, tuple) and len(error_detail) == 2 and "1064" in str(error_detail[0]):
                        # 重新尝试修复SQL (针对MySQL 1064错误)
                        print("检测到MySQL 1064语法错误，尝试修复...")
                        if has_semicolon:
                            # 如果本来有分号但被去掉了，试着加回来
                            fixed_sql = sql_query + ";"
                            print(f"添加分号后重新尝试执行SQL: {fixed_sql[:100]}...")
                            return execute_query(fixed_sql)  # 递归调用自身，尝试修复后的SQL
                    raise ValueError(f"API错误: {error_data['error']}")
            except (json.JSONDecodeError, KeyError):
                pass  # 如果无法解析API错误，使用默认异常
        # 未能提取API具体错误，则重新抛出原始异常
        raise
    
    except json.JSONDecodeError as e:
        print(f"解码 execute_query 的 JSON 响应时出错: {e}")
        raise ValueError(f"来自 {api_url} 的无效 JSON 响应")


def update_record(update_payload: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    调用 Flask API 端点以更新数据库中的记录。

    对应 Dify 节点 '1742354001584' 中的 API 调用。

    参数:
        update_payload: 一个字典列表，每个字典代表一个更新操作
                        (包含 table_name, primary_key, primary_value, update_fields)。

    返回:
        一个字典列表，代表每个更新操作的结果。
    抛出:
        requests.exceptions.RequestException: 如果 API 请求失败。
        ValueError: 如果响应不是有效的 JSON。
    """
    api_url = f"{BASE_API_URL}/update_record"
    try:
        print(f"调试: 发送更新负载: {json.dumps(update_payload, ensure_ascii=False)}") # 类似 Dify code 中的调试行
        response = requests.post(api_url, headers=HEADERS, json=update_payload, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"调用 update_record API 时出错: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"解码 update_record 的 JSON 响应时出错: {e}")
        raise ValueError(f"来自 {api_url} 的无效 JSON 响应")


def insert_record(insert_payload: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    调用 Flask API 端点以向数据库插入新记录。

    对应 Dify 节点 '1742439055405' 中的 API 调用。

    参数:
        insert_payload: 一个字典列表，每个字典代表一个插入操作
                        (包含 table_name, fields)。

    返回:
        一个字典，代表插入操作的结果 (例如: {"message": "..."})。
    抛出:
        requests.exceptions.RequestException: 如果 API 请求失败。
        ValueError: 如果响应不是有效的 JSON或包含API错误信息。
    """
    api_url = f"{BASE_API_URL}/insert_record"
    try:
        print(f"调试: 发送插入负载: {json.dumps(insert_payload, ensure_ascii=False)}") # 类似 Dify code 中的调试行
        response = requests.post(api_url, headers=HEADERS, json=insert_payload, timeout=TIMEOUT)
        
        # 记录API响应，帮助调试
        print(f"插入记录API响应状态码: {response.status_code}")
        print(f"插入记录API响应内容: {response.text[:500]}...")
        
        # 如果是错误响应，尝试从响应内容提取有用信息
        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"解析到的错误数据: {error_data}")
                if isinstance(error_data, dict) and "error" in error_data:
                    error_message = error_data["error"]
                    print(f"API错误详情: {error_message}")
                    # 将API返回的错误消息抛出，保留完整信息
                    raise ValueError(f"API错误: {error_message}")
                else:
                    print(f"错误响应格式异常: {error_data}")
                    raise ValueError(f"API错误: 未知错误格式")
            except json.JSONDecodeError as json_err:
                # 如果无法解析JSON错误响应，使用原始内容
                error_content = response.text[:200] + ("..." if len(response.text) > 200 else "")
                print(f"API返回非JSON错误响应: {error_content}")
                raise ValueError(f"API错误: 无法解析错误响应 - {error_content}")
        
        # 正常处理响应
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"调用 insert_record API 时出错: {e}")
        print(f"异常类型: {type(e)}")
        # 检查是否有API返回的错误信息
        if hasattr(e, 'response') and e.response is not None:
            print(f"异常中的响应状态码: {e.response.status_code}")
            print(f"异常中的响应内容: {e.response.text[:500]}...")
            try:
                error_data = e.response.json()
                print(f"从异常响应中解析到的错误数据: {error_data}")
                if isinstance(error_data, dict) and "error" in error_data:
                    # 提取API返回的具体错误信息
                    error_detail = error_data['error']
                    print(f"提取到Flask具体错误信息: {error_detail}")
                    raise ValueError(f"API错误: {error_detail}")
                else:
                    print(f"异常响应格式异常: {error_data}")
                    raise ValueError(f"API错误: {error_data}")
            except (json.JSONDecodeError, KeyError) as parse_err:
                print(f"解析异常响应时出错: {parse_err}")
                # 如果无法解析API错误，使用原始异常信息
                raw_content = e.response.text[:200] + ("..." if len(e.response.text) > 200 else "")
                raise ValueError(f"API错误: 无法解析异常响应 - {raw_content}")
        # 未能提取API具体错误，则重新抛出原始异常
        print("异常中没有响应信息，重新抛出原始异常")
        raise
    except json.JSONDecodeError as e:
        print(f"解码 insert_record 的 JSON 响应时出错: {e}")
        raise ValueError(f"来自 {api_url} 的无效 JSON 响应")

def delete_record(table_name: str, primary_key: str, primary_value: Any) -> Dict[str, Any]:
    """
    调用 Flask API 端点以删除特定记录。

    对应 Dify 节点 '1742520996237' 循环内的 API 调用。

    参数:
        table_name: 表名。
        primary_key: 主键列名。
        primary_value: 要删除记录的主键值。

    返回:
        一个字典，代表操作结果 (例如: {"message": ...} 或 {"error": ...})。
    抛出:
        requests.exceptions.RequestException: 如果 API 请求失败。
        ValueError: 如果响应不是有效的 JSON。
    """
    api_url = f"{BASE_API_URL}/delete_record"
    payload = {
        "table_name": table_name,
        "primary_key": primary_key,
        "primary_value": primary_value
    }
    try:
        response = requests.post(api_url, headers=HEADERS, json=payload, timeout=TIMEOUT)
        
        # 记录更详细的响应信息，帮助调试
        print(f"删除记录API响应: 状态码={response.status_code}, 内容={response.text[:100]}...")
        
        # 检查是否是404错误（记录不存在），如果是，继续处理而不抛出异常
        if response.status_code == 404:
            try:
                error_data = response.json()
                if "error" in error_data and "No record found" in error_data["error"]:
                    # 这是记录不存在的情况，不是错误
                    print(f"表 {table_name} 中没有找到主键值为 {primary_value} 的记录，但操作完成")
                    return {"message": f"Record with {primary_key}={primary_value} not found, but operation completed"}
            except (json.JSONDecodeError, KeyError):
                # 如果无法解析响应JSON，可能是真正的端点不存在问题
                pass
        
        # 对其他错误状态码抛出异常
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"调用 delete_record API 时出错 (表: {table_name}, 主键值: {primary_value}): {e}")
        # 增加错误处理逻辑，检查是否是端点不可用的问题
        if "404" in str(e) or "Not Found" in str(e):
            print(f"警告: 删除端点404错误。这可能是因为记录不存在或API端点问题。")
            # 我们返回一个模拟的成功响应，以避免中断整个删除流程
            return {"message": f"Record with {primary_key}={primary_value} possibly deleted, endpoint returned 404"}
        raise
    except json.JSONDecodeError as e:
        print(f"解码 delete_record 的 JSON 响应时出错: {e}")
        raise ValueError(f"来自 {api_url} 的无效 JSON 响应")

# === 新增：批量操作 API 调用 ===
def execute_batch_operations(operations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    调用 Flask API 端点以原子方式执行一批数据库操作（更新、插入等）。
    对应方案三中的新后端端点。

    参数:
        operations: 一个操作字典的列表，每个字典描述一个操作。
                    格式待定，但应包含操作类型、表、数据、依赖等信息。
                    例如: 
                    [
                      {"operation": "update", "table_name": "t1", ...},
                      {"operation": "insert", "table_name": "t2", ...}
                    ]

    返回:
        一个字典，代表整个批处理操作的结果（成功或失败信息）。
    抛出:
        requests.exceptions.RequestException: 如果 API 请求失败。
        ValueError: 如果响应不是有效的 JSON或包含API错误信息。
    """
    api_url = f"{BASE_API_URL}/execute_batch_operations" # 新的端点 URL
    try:
        print(f"调试: 发送批量操作负载: {json.dumps(operations, ensure_ascii=False)}")
        # 注意：超时时间可能需要根据操作复杂性调整
        response = requests.post(api_url, headers=HEADERS, json=operations, timeout=TIMEOUT * 3) # 稍微延长超时
        
        # 记录API响应，帮助调试
        print(f"批量操作API响应状态码: {response.status_code}")
        
        # 如果是错误响应，尝试从响应内容提取有用信息
        if response.status_code != 200:
            try:
                error_data = response.json()
                if isinstance(error_data, dict) and "error" in error_data:
                    error_message = error_data["error"]
                    
                    # 检查是否有详细错误信息（特别是重复约束错误）
                    error_detail = error_data.get("detail")
                    if error_detail and isinstance(error_detail, dict):
                        # 如果是重复约束错误，使用更详细的信息
                        if error_detail.get("type") == "IntegrityError.DuplicateEntry":
                            # 使用原始数据库错误信息，包含具体字段和值
                            original_error = error_detail.get("original_error", "")
                            if original_error:
                                # 直接使用数据库的详细错误信息，如："Duplicate entry '张三丰' for key 'users.username'"
                                detailed_message = original_error
                            else:
                                # 回退方案：构造错误信息
                                table_name = error_detail.get("table_name", "")
                                key_name = error_detail.get("key_name", "")
                                conflicting_value = error_detail.get("conflicting_value", "")
                                operation_index = error_detail.get("failed_operation_index", "")
                                detailed_message = f"批量操作第{operation_index}步失败: 表{table_name}的{key_name}字段值'{conflicting_value}'已存在"
                            
                            print(f"API详细错误信息: {detailed_message}")
                            raise ValueError(f"API错误: {detailed_message}")
                    
                    print(f"API错误详情: {error_message}")
                    # 将API返回的错误消息抛出，保留完整信息
                    raise ValueError(f"API错误: {error_message}")
            except json.JSONDecodeError:
                # 如果无法解析JSON错误响应，使用原始内容
                error_content = response.text[:200] + ("..." if len(response.text) > 200 else "")
                print(f"API返回非JSON错误响应: {error_content}")
        
        # 正常处理响应
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"调用 execute_batch_operations API 时出错: {e}")
        # 检查是否有API返回的错误信息
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                if isinstance(error_data, dict) and "error" in error_data:
                    # 提取API返回的具体错误信息
                    error_detail = error_data['error']
                    print(f"提取到Flask具体错误信息: {error_detail}")
                    raise ValueError(f"API错误: {error_data['error']}")
            except (json.JSONDecodeError, KeyError):
                pass  # 如果无法解析API错误，使用默认异常
        # 未能提取API具体错误，则重新抛出原始异常
        raise
    except json.JSONDecodeError as e:
        print(f"解码 execute_batch_operations 的 JSON 响应时出错: {e}")
        raise ValueError(f"来自 {api_url} 的无效 JSON 响应") 