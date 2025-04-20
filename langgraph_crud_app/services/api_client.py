# api_client.py: 封装了向后端 Flask API 发送 HTTP 请求的逻辑。

import requests
import json
from typing import List, Dict, Any, Optional

# --- 配置 ---
# TODO: 后续将此 URL 移至 config/settings.py 以进行更好的管理
BASE_API_URL = "http://192.168.0.32:5003"
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
        ValueError: 如果响应不是有效的 JSON。
    """
    api_url = f"{BASE_API_URL}/execute_query"
    payload = {"sql_query": sql_query}
    try:
        response = requests.post(api_url, headers=HEADERS, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        # Dify code 节点期望结果直接是 JSON 字符串
        # Flask API 返回 JSON 列表，因此我们将其转储回字符串
        result_data = response.json()
        return json.dumps(result_data, ensure_ascii=False)
    except requests.exceptions.RequestException as e:
        print(f"调用 execute_query API 时出错: {e}")
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
        ValueError: 如果响应不是有效的 JSON。
    """
    api_url = f"{BASE_API_URL}/insert_record"
    try:
        print(f"调试: 发送插入负载: {json.dumps(insert_payload, ensure_ascii=False)}") # 类似 Dify code 中的调试行
        response = requests.post(api_url, headers=HEADERS, json=insert_payload, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"调用 insert_record API 时出错: {e}")
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
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"调用 delete_record API 时出错 (表: {table_name}, 主键值: {primary_value}): {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"解码 delete_record 的 JSON 响应时出错: {e}")
        raise ValueError(f"来自 {api_url} 的无效 JSON 响应") 