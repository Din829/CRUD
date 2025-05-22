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
from langgraph_crud_app.services.llm import llm_error_service  # 新增：导入错误处理服务
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
                logger.info(f"解析数据库占位符 '{value}'，查询语句: {subquery}")
                result_str = api_client.execute_query(subquery)
                result = json.loads(result_str)

                if isinstance(result, list):
                    if not result:  # 空列表 []
                        logger.info(f"数据库子查询 '{subquery}' 返回空列表。占位符解析为 []。")
                        return [] # 返回空列表，由API层处理IN ([])的情况
                    
                    is_list_of_single_kv_dicts = True
                    if not all(isinstance(row, dict) and len(row) == 1 for row in result):
                        is_list_of_single_kv_dicts = False

                    if len(result) == 1 and is_list_of_single_kv_dicts: # 单行单列，严格的单值
                        actual_value = list(result[0].values())[0]
                        logger.info(f"数据库占位符 '{value}' (单值) 解析为 '{actual_value}'")
                        return _process_value(actual_value) # 递归处理以防值本身也是占位符
                    elif is_list_of_single_kv_dicts: # 多行单列 (例如用于 IN 子句)
                        actual_values_list = [list(row.values())[0] for row in result]
                        logger.info(f"数据库占位符 '{value}' (值列表) 解析为 {actual_values_list}")
                        return actual_values_list 
                    else: # 格式不符合单值或单列列表 (例如返回了多列)
                        logger.error(f"数据库子查询 '{subquery}' 结果格式非单值或单列值列表。结果: {result}")
                        return None # 视为解析失败
                else: # API 返回的不是列表格式 (理论上不应发生，execute_query 应返回列表或抛异常)
                    logger.error(f"数据库子查询 '{subquery}' 来自 API 的结果非预期列表格式。结果: {result}")
                    return None # 视为解析失败
            except Exception as e:
                logger.error(f"执行数据库子查询 '{subquery}' 时出错: {e}")
                # 使用新的错误处理服务转换API错误为用户友好信息
                try:
                    friendly_error = llm_error_service.translate_flask_error(
                        error_info=str(e),
                        operation_context={
                            "user_query": subquery,
                            "operation_type": "数据库查询",
                            "tables_involved": "数据库查询"
                        }
                    )
                    logger.info(f"数据库查询错误的用户友好信息: {friendly_error}")
                    # 这里我们仍然返回None表示占位符解析失败，但错误信息已经被处理
                    # 在更高层级的函数中可以访问这个友好错误信息
                except Exception as err_service_error:
                    logger.warning(f"错误处理服务也失败了: {err_service_error}")
                return None

        # 处理 random 占位符
        random_match = re.match(r'\{\{random\((.*?)\)\}\}', value) # 修改：使用正则表达式匹配 random 占位符
        logger.debug(f"_process_value: Attempting random_match. Original value=REPR<{repr(value)}>. Match object: {random_match}") # 新增调试日志
        if random_match:
            random_type = random_match.group(1).strip().lower() # 修改：提取类型
            random_value = None
            if random_type == 'string':
                random_value = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            elif random_type == 'integer':
                random_value = random.randint(10000, 99999) # 调整范围示例
            elif random_type == 'uuid':
                random_value = str(uuid.uuid4())
            elif random_type == 'japanese_name_4_chars': # 新增临时处理分支
                # 临时方案: 生成一个4位的随机字母数字字符串，以通过当前流程测试
                # 注意：这不生成真正的日文名，仅用于调试和流程验证
                random_value = ''.join(random.choices(string.ascii_letters + string.digits, k=4))
                logger.info(f"临时处理 random type '{random_type}', 生成值: {random_value}")
            else:
                 logger.warning(f"不支持的随机类型: {random_type}")
                 return None
            logger.info(f"随机占位符 '{value}' 解析为 '{random_value}'")
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
    新增逻辑：过滤掉因占位符解析导致外键字段值为列表的无效 insert 操作。
    """
    logger.info("---节点: 处理复合操作占位符---")
    plan_to_process = state.get("lastest_content_production")

    if not plan_to_process:
        logger.warning("用于执行的操作计划为空，无需处理占位符。")
        return {} # 返回空字典，表示没有更新

    if not isinstance(plan_to_process, list):
        logger.error(f"操作计划格式错误 (非列表: {type(plan_to_process)})，无法处理占位符。")
        return {"error_message": "操作计划状态错误。", "lastest_content_production": None}

    interim_processed_plan: List[Dict[str, Any]] = []
    has_placeholder_processing_error = False

    try:
        for i, operation in enumerate(plan_to_process):
            processed_operation = {} 
            for op_key, op_value in operation.items():
                if op_key in ["values", "set", "where"] and isinstance(op_value, dict):
                    processed_dict = {} 
                    for field_key, field_value in op_value.items():
                         should_process = True # 默认需要处理
                         is_potential_sql_expression = False

                         if op_key == "set" and isinstance(field_value, str):
                             # 检查是否像SQL函数调用或简单赋值表达式 (不含我们的占位符模式)
                             if (re.search(r'\w+\(.*?\)', field_value) or # 像 func(...)
                                 re.search(r'\w+\s*[+\-*/%&|^<>!=]+\s*\w+', field_value) or # 像 a + b, count > 0
                                 re.match(r"^\w+\s*=\s*\w+$", field_value) or # 像 field = other_field (但不常见于set的值)
                                 field_value.upper() == 'NOW()'): # 特殊处理 NOW()
                                 
                                 # 如果它不是以 {{ 开头并以 }} 结尾的占位符，则认为是 SQL 表达式
                                 if not (field_value.startswith("{{") and field_value.endswith("}}")):
                                     is_potential_sql_expression = True
                         
                         if is_potential_sql_expression:
                             logger.debug(f"在 'set' 子句中跳过对潜在SQL表达式的占位符处理: {field_key}={field_value}")
                             should_process = False
                         
                         if should_process:
                              processed_val = _process_value(field_value)
                              if processed_val is None and field_value is not None: # field_value is not None 检查确保我们只标记真正失败的解析
                                   logger.error(f"处理占位符失败 操作索引 {i}, 表 '{operation.get('table_name', '未知')}', 字段 '{field_key}': 原值 '{field_value}'")
                                   has_placeholder_processing_error = True
                                   processed_dict[field_key] = None 
                              else:
                                   processed_dict[field_key] = processed_val
                         else:
                              processed_dict[field_key] = field_value 
                    processed_operation[op_key] = processed_dict
                else:
                     processed_operation[op_key] = op_value
            
            interim_processed_plan.append(processed_operation)
            if has_placeholder_processing_error:
                 logger.warning(f"在操作索引 {i} 处检测到占位符处理错误，停止后续操作的占位符处理。")
                 break
    
    except Exception as e:
        logger.exception(f"处理复合操作占位符时发生意外错误: {e}")
        return {"error_message": f"处理占位符时系统内部错误: {e}", "lastest_content_production": None}

    if has_placeholder_processing_error:
         logger.error("由于处理占位符时至少发生一处错误，操作计划可能不完整或无效。")
         return {"error_message": "处理占位符时出错，部分或全部操作可能无法执行。", "lastest_content_production": None}

    # --- 新增：过滤无效的 INSERT 操作 ---
    final_executable_plan: List[Dict[str, Any]] = []
    for op_detail in interim_processed_plan:
        skip_this_operation = False
        if op_detail.get("operation") == "insert":
            values_to_insert = op_detail.get("values")
            if isinstance(values_to_insert, dict):
                for field, value in values_to_insert.items():
                    if isinstance(value, list):
                        table_name_for_log = op_detail.get('table_name', '未知表')
                        logger.warning(
                            f"字段 '{field}' 在表 '{table_name_for_log}' 的插入操作中 "
                            f"通过占位符处理后解析为一个列表: {value} (类型: {type(value)})。 "
                            f"假设此字段期望标量值。将跳过此插入操作。"
                        )
                        skip_this_operation = True
                        break # 一个字段是列表就足以跳过此 insert 操作
        
        if not skip_this_operation:
            final_executable_plan.append(op_detail)
        else:
            logger.info(f"因字段值为列表而省略的插入操作: {op_detail}")
    # --- 过滤逻辑结束 ---

    original_plan_count = len(plan_to_process)
    interim_plan_count = len(interim_processed_plan)
    final_plan_count = len(final_executable_plan)

    logger.info(
        f"占位符处理完成。原始计划条数: {original_plan_count}, "
        f"占位符处理后（错误检查前）条数: {interim_plan_count}, "
        f"最终可执行计划条数 (过滤后): {final_plan_count}"
    )
    if final_plan_count < interim_plan_count :
        logger.info(f"{interim_plan_count - final_plan_count} 个插入操作因字段值为列表而被省略。")

    logger.debug(f"最终可执行计划 (用于API): {final_executable_plan}")
    return {"lastest_content_production": final_executable_plan, "error_message": None}

def format_combined_preview_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：调用 LLM 服务将结构化的复合操作计划格式化为用户友好的预览文本。
    现在读取 combined_operation_plan (原始计划带占位符) 用于预览。
    """
    logger.info("---节点: 格式化复合操作预览---")
    user_query = state.get("user_query", "")
    # 修改：读取原始计划用于预览，而不是处理后的计划
    combined_plan_for_preview = state.get("combined_operation_plan")
    # 同时获取处理后的计划，以供LLM参考，了解哪些操作可能不会执行
    processed_plan_for_context = state.get("lastest_content_production")

    if not combined_plan_for_preview:
        logger.warning("原始复合操作计划为空，无法生成预览。")
        no_op_preview = "未能解析出任何有效的操作，或所有解析出的操作都因数据问题而无法执行。"
        # 即使原始计划为空，也要确保 lastest_content_production 也被清空或设为[]
        # parse_combined_request_action 在 plan 为空时返回 lastest_content_production: None
        # 如果 process_composite_placeholders_action 因 plan_to_process 为空而提前返回 {}，
        # 那么 lastest_content_production 可能还是旧值，这里确保它是空列表
        if state.get("lastest_content_production") is not None and not state.get("lastest_content_production"): #  is not None but empty
             pass # it's already an empty list or similar, good.
        elif not state.get("lastest_content_production"): # it is None or truly empty
             pass # good
        else: # It has content that might be stale if combined_plan_for_preview is empty
             logger.info("原始计划为空，但处理后计划非空，可能不一致，预览时通知用户无操作。")

        return {"content_combined": no_op_preview, "lastest_content_production": state.get("lastest_content_production") if combined_plan_for_preview else [], "pending_confirmation_type": None}

    if not isinstance(combined_plan_for_preview, list):
        logger.error(f"原始复合操作计划格式错误 (非列表: {type(combined_plan_for_preview)})，无法生成预览。")
        return {"error_message": "复合操作计划状态错误，无法生成预览。", "content_combined": None, "pending_confirmation_type": None}

    try:
        # LLM 现在可以同时拿到原始计划（主要用于措辞）和实际执行计划（用于准确性）
        preview_text = llm_composite_service.format_combined_preview(
            user_query=user_query,
            combined_operation_plan=combined_plan_for_preview, # 原始计划，带占位符
            # 可选：传递处理后的计划，让LLM知道哪些操作可能被省略
            # actual_executable_plan=processed_plan_for_context
        )
        logger.info(f"生成复合操作预览文本: {preview_text}")
        return {
            "content_combined": preview_text, 
            "error_message": None,
            "pending_confirmation_type": "composite" # 设置待确认类型
        }

    except Exception as e:
        logger.exception(f"调用 LLM 格式化复合预览时发生错误: {e}")
        plan_str_fallback = json.dumps(combined_plan_for_preview, ensure_ascii=False, indent=2)
        fallback_preview = f"无法生成清晰的预览。将尝试执行以下原始操作计划（占位符未处理，部分操作可能因数据无效而跳过），请谨慎确认：\\n{plan_str_fallback}"
        return {
            "error_message": f"生成复合预览时出错: {e}", 
            "content_combined": fallback_preview,
            "pending_confirmation_type": None # 出错，不设置或清除
        } 