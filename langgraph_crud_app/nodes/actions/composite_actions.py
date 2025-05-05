"""
包含处理复合操作（如同时修改和新增）的动作节点。
"""

import logging
from typing import Dict, Any, List
import json
import random
import string
import uuid
import re # 确保导入 re

from langgraph_crud_app.graph.state import GraphState
from langgraph_crud_app.services.llm import llm_composite_service
from langgraph_crud_app.services import api_client # 需要 API Client

logger = logging.getLogger(__name__)

# === 复合操作解析与预览动作节点 ===

def parse_combined_request_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：调用 LLM 服务解析用户的复合请求，生成结构化的操作计划列表。
    """
    logger.info("---节点: 解析复合请求---")
    user_query = state.get("user_query", "")
    schema_info = state.get("biaojiegou_save", "")
    table_names = state.get("table_names", [])
    sample_data = state.get("data_sample", "")

    if not user_query:
        logger.warning("用户查询为空，无法解析复合请求。")
        return {"error_message": "用户查询为空，无法解析复合请求。"}
    if not schema_info or not table_names:
        logger.error("数据库 Schema 或表名列表为空，无法解析复合请求。")
        return {"error_message": "数据库元数据缺失，无法解析复合请求。"}

    try:
        combined_plan = llm_composite_service.parse_combined_request(
            user_query=user_query,
            schema_info=schema_info,
            table_names=table_names,
            sample_data=sample_data
        )

        if not combined_plan: # LLM 返回空列表，表示无法解析或无有效操作
            logger.info("LLM 未能从用户查询中解析出有效的复合操作计划。")
            # 暂时先不设置 final_answer，让图继续流转
            # 清除 lastest_content_production 以防万一
            return {"combined_operation_plan": [], "lastest_content_production": None}

        logger.info(f"成功解析出复合操作计划: {combined_plan}")
        # 将解析出的计划存储到状态中
        # 注意：初始时，两者都存原始计划。占位符处理节点会更新 lastest_content_production
        return {
            "combined_operation_plan": combined_plan,
            "lastest_content_production": combined_plan, # 暂存原始计划
            "error_message": None # 清除之前的错误
        }

    except ValueError as e:
        logger.error(f"调用 LLM 解析复合请求失败: {e}")
        return {"error_message": f"解析复合请求时出错: {e}", "combined_operation_plan": None, "lastest_content_production": None}
    except Exception as e:
        logger.exception(f"解析复合请求时发生意外错误: {e}")
        return {"error_message": f"处理复合请求时发生系统内部错误: {e}", "combined_operation_plan": None, "lastest_content_production": None}

# === 新增：占位符处理辅助函数和动作节点 ===

def _process_value(value: Any): # 移除 cursor 参数，使用全局 api_client
    """递归处理值中的占位符 (db 和 random)。"""
    if isinstance(value, str):
        # 优先处理 db 占位符
        db_match = re.match(r'\{\{db\((.*?)\)\}\}', value) # 修改：使用正则表达式匹配 db 占位符
        if db_match:
            subquery = db_match.group(1).strip() # 修改：提取子查询
            try:
                logger.info(f"Resolving db placeholder '{value}' with query: {subquery}")
                # 注意：直接执行子查询可能不安全
                result = api_client.execute_query(subquery) # 使用导入的 client
                if result and len(result) == 1 and len(result[0]) == 1:
                    actual_value = list(result[0].values())[0]
                    logger.info(f"Resolved db placeholder '{value}' to '{actual_value}'")
                    return _process_value(actual_value)
                else:
                    logger.error(f"Subquery '{subquery}' did not return exactly one value. Result: {result}")
                    return None
            except Exception as e:
                logger.error(f"Error executing subquery '{subquery}': {e}")
                return None

        # 处理 random 占位符
        random_match = re.match(r'\{\{random\((.*?)\)\}\}', value) # 修改：使用正则表达式匹配 random 占位符
        if random_match:
            random_type = random_match.group(1).strip().lower() # 修改：提取类型
            random_value = None
            if random_type == 'string':
                random_value = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            elif random_type == 'integer':
                random_value = random.randint(10000, 99999) # 调整范围示例
            elif random_type == 'uuid':
                random_value = str(uuid.uuid4())
            else:
                 logger.warning(f"Unsupported random type: {random_type}")
                 return None
            logger.info(f"Resolved random placeholder '{value}' to '{random_value}'")
            return random_value

    elif isinstance(value, dict):
        # 递归处理字典的值
        return {k: _process_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        # 递归处理列表的元素
        return [_process_value(item) for item in value]

    return value # 返回原值

def process_composite_placeholders_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：处理复合操作计划中的 {{db(...)}} 和 {{random(...)}} 占位符。
    更新 lastest_content_production 状态。
    """
    logger.info("---节点: 处理复合操作占位符---")
    # 使用 lastest_content_production 作为输入和输出，因为它将用于执行
    plan_to_process = state.get("lastest_content_production")

    if not plan_to_process:
        logger.warning("用于执行的操作计划为空，无需处理占位符。")
        return {}

    if not isinstance(plan_to_process, list):
        logger.error(f"操作计划格式错误 (非列表: {type(plan_to_process)})，无法处理占位符。")
        # 清除 plan 以阻止后续执行
        return {"error_message": "操作计划状态错误。", "lastest_content_production": None}

    processed_plan = []
    has_error = False

    try:
        # 注意：这里直接修改传入的列表（来自 state）可能不是最佳实践
        # 但考虑到 LangGraph 的状态更新机制，这通常是有效的
        # 如果需要更严格的隔离，应该先深拷贝
        for i, operation in enumerate(plan_to_process):
            processed_operation = {} # 创建新的字典存储处理后的操作
            for op_key, op_value in operation.items():
                if op_key in ["values", "set", "where"] and isinstance(op_value, dict):
                    processed_dict = {} # 创建新的字典存储处理后的字典
                    for field_key, field_value in op_value.items():
                         # 对 set 中的值进行特殊处理，避免处理 SQL 表达式
                         should_process = True
                         if op_key == "set" and isinstance(field_value, str) and ('(' in field_value or '+' in field_value or '-' in field_value):
                             # 简单的启发式检查，可以改进
                             logger.debug(f"Skipping placeholder processing for potential SQL expression in set: {field_key}={field_value}")
                             should_process = False
                         
                         if should_process:
                              processed_val = _process_value(field_value)
                              if processed_val is None and field_value is not None:
                                   logger.error(f"处理占位符失败 操作索引 {i}, 字段 '{field_key}': {field_value}")
                                   has_error = True
                                   # 可以选择是停止整个处理还是仅标记此字段处理失败
                                   # 暂时选择继续处理其他字段，但标记全局错误
                                   processed_dict[field_key] = None # 标记处理失败
                              else:
                                   processed_dict[field_key] = processed_val
                         else:
                              processed_dict[field_key] = field_value # 保留未处理的值
                    processed_operation[op_key] = processed_dict
                else:
                     # 复制其他键值对（如 operation, table_name, depends_on_index 等）
                     processed_operation[op_key] = op_value
            
            processed_plan.append(processed_operation)
            # 如果在处理当前操作时发生错误，立即停止
            if has_error:
                 break

        if has_error:
             logger.error("处理占位符时至少发生一处错误。")
             # 清除计划以阻止执行
             return {"error_message": "处理占位符时出错。", "lastest_content_production": None}
        else:
             logger.info(f"成功处理占位符，更新后的计划 (用于执行): {processed_plan}")
             return {"lastest_content_production": processed_plan, "error_message": None}

    except Exception as e:
        logger.exception(f"处理复合操作占位符时发生意外错误: {e}")
        # 清除计划以阻止执行
        return {"error_message": f"处理占位符时系统内部错误: {e}", "lastest_content_production": None}

def format_combined_preview_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：调用 LLM 服务将结构化的复合操作计划格式化为用户友好的预览文本。
    现在读取 combined_operation_plan (原始计划带占位符) 用于预览。
    """
    logger.info("---节点: 格式化复合操作预览---")
    user_query = state.get("user_query", "")
    # 修改：读取原始计划用于预览，而不是处理后的计划
    combined_plan_for_preview = state.get("combined_operation_plan")

    if not combined_plan_for_preview:
        logger.warning("原始复合操作计划为空，无法生成预览。")
        # 如果计划为空，意味着解析失败或无操作
        # 提供一个明确的无操作反馈可能更好
        no_op_preview = "未能解析出任何有效的操作。"
        return {"content_combined": no_op_preview}

    if not isinstance(combined_plan_for_preview, list):
        logger.error(f"原始复合操作计划格式错误 (非列表: {type(combined_plan_for_preview)})，无法生成预览。")
        return {"error_message": "复合操作计划状态错误，无法生成预览。", "content_combined": None}

    try:
        preview_text = llm_composite_service.format_combined_preview(
            user_query=user_query,
            combined_operation_plan=combined_plan_for_preview # 使用原始计划
        )
        logger.info(f"生成复合操作预览文本: {preview_text}")
        # 清除错误消息，因为预览成功了
        return {"content_combined": preview_text, "error_message": None}

    except Exception as e:
        logger.exception(f"调用 LLM 格式化复合预览时发生错误: {e}")
        # 格式化预览失败也设置错误，但保留 content_combined 作为回退
        plan_str_fallback = json.dumps(combined_plan_for_preview, ensure_ascii=False, indent=2)
        fallback_preview = f"无法生成清晰的预览。将尝试执行以下操作计划（占位符未处理），请谨慎确认：\n{plan_str_fallback}"
        return {"error_message": f"生成复合预览时出错: {e}", "content_combined": fallback_preview} 