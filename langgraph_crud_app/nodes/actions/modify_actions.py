"""
包含与处理修改意图相关的动作节点。
"""

from typing import Dict, Any
import json
import logging # 导入 logging 模块

# 导入状态定义和服务
from langgraph_crud_app.graph.state import GraphState
from langgraph_crud_app.services.llm import llm_modify_service
from langgraph_crud_app.services import api_client

# 获取 logger 实例
logger = logging.getLogger(__name__)

# --- 新增：修改流程 - 上下文查询 SQL 生成节点 ---

def generate_modify_context_sql_action(state: GraphState) -> Dict[str, Any]:
    """
    LLM 生成用于获取修改操作所需上下文的 SELECT SQL。
    修改：在生成 SQL 前，调用 LLM 服务检查用户查询是否明确要求修改 ID。
    """
    query = state.get('user_query')
    if not query:
        return {"error_message": "用户查询为空，无法生成修改上下文 SQL。"}

    # --- 修改：调用 LLM 服务检查用户查询 ---
    try:
        # 假设新函数名为 check_for_direct_id_modification_intent
        # 这个函数如果检测到不允许的意图，应返回错误消息字符串；否则返回 None
        rejection_message = llm_modify_service.check_for_direct_id_modification_intent(query)

        if rejection_message:
            logger.warning(f"拒绝操作：LLM 检测到用户查询 '{query}' 包含明确修改 ID 的意图。")
            # 直接返回错误，阻止后续流程
            return {
                "final_answer": rejection_message, 
                "error_message": "Explicit ID change intent detected by LLM and rejected.", # 内部错误标记
                "modify_context_sql": None # 确保不执行后续SQL
            }
        
        # 如果没有被拒绝，则继续正常流程
        logger.info("LLM 未检测到明确修改 ID 的意图，继续生成上下文 SQL。")

    except Exception as e:
        # 处理调用 LLM 服务本身可能发生的错误
        error_msg = f"检查修改 ID 意图时发生错误: {e}"
        logger.error(error_msg)
        # 出现检查错误时，为保守起见，可以选择阻止流程或允许流程继续（带警告）
        # 这里选择阻止流程，返回错误给用户
        return {
            "error_message": error_msg, 
            "final_answer": "抱歉，在分析您的请求意图时遇到内部错误，无法继续处理。",
            "modify_context_sql": None
        }
    # --- 检查结束 ---

    logger.info("---节点: 生成修改上下文查询 SQL---")
    biaojiegou_save = state.get('biaojiegou_save')
    tables = state.get("table_names")
    sample = state.get("data_sample")

    # 检查必需的元数据是否存在
    if not all([biaojiegou_save, tables, sample]):
        error_msg = "生成上下文 SQL 失败：缺少数据库元数据。"
        logger.error(error_msg)
        return {"error_message": error_msg, "modify_context_sql": None}

    try:
        # 调用 LLM 服务生成 SQL
        context_sql = llm_modify_service.generate_modify_context_sql(
            query=query,
            schema_str=biaojiegou_save,
            table_names=tables,
            data_sample_str=sample
        )

        if not context_sql:
            # LLM 服务未能生成有效 SQL
            error_msg = "无法根据您的请求生成用于获取上下文的查询。请尝试更清晰地描述您的修改意图。"
            logger.warning(error_msg)
            # 设置 final_answer 而不是 error_message，让流程直接结束回复用户
            return {"final_answer": error_msg, "modify_context_sql": None}

        # 成功生成 SQL
        return {"modify_context_sql": context_sql, "error_message": None}

    except Exception as e:
        error_msg = f"生成修改上下文 SQL 时发生错误: {e}"
        logger.error(error_msg)
        return {"error_message": error_msg, "modify_context_sql": None}

# --- 新增：修改流程 - 上下文查询 SQL 执行节点 ---

def execute_modify_context_sql_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：执行为获取修改上下文而生成的 SELECT SQL。
    """
    logger.info("---节点: 执行修改上下文查询 SQL---")
    context_sql = state.get("modify_context_sql")
    error_message = state.get("error_message") # 保留上一步可能设置的错误

    # 如果上一步生成 SQL 就失败了，直接返回
    if error_message or not context_sql:
        logger.info("上一步生成上下文 SQL 失败或出错，跳过执行。")
        # 注意：这里不应清除 error_message，如果它已设置
        # 如果 context_sql 为空但没错误（LLM 返回澄清），则上一步已设置 final_answer
        return {"modify_context_result": None} 

    try:
        # 调用 API Client 执行查询
        # 注意：api_client.execute_query 内部处理了异常并会 raise
        query_result_str = api_client.execute_query(context_sql)
        logger.info(f"上下文查询结果: {query_result_str}")

        # 检查返回结果是否表示未找到数据 (例如，返回 '[]')
        # 即使查不到数据，对于修改流程也可能是有用的信息 (例如，记录不存在)
        # 因此，我们存储结果，但不将其视为错误。
        # if not query_result_str or query_result_str.strip() == '[]':
        #     print("上下文查询未返回任何数据。")

        # 清除可能从上一步传递过来的错误（如果执行成功）
        return {"modify_context_result": query_result_str, "error_message": None}

    except Exception as e:
        # 捕获 api_client.execute_query 可能抛出的异常
        error_msg = f"执行修改上下文查询时出错: {e}"
        logger.error(error_msg)
        return {"error_message": error_msg, "modify_context_result": None}

# --- 修改流程动作节点 ---

def parse_modify_request_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：调用 LLM 服务解析用户的修改请求，利用上下文查询结果。
    """
    logger.info("---节点: 解析修改请求--- marginalised")
    query = state.get("user_query", "")
    schema = state.get("biaojiegou_save")
    tables = state.get("table_names")
    sample = state.get("data_sample")
    # 新增：获取上下文查询结果
    context_result = state.get("modify_context_result")
    error_message = state.get("error_message") # 保留上一步可能设置的错误

    # 如果上一步执行上下文查询出错，直接传递错误
    if error_message:
        logger.info(f"上一步骤 (执行上下文查询) 存在错误: {error_message}")
        return {"error_message": error_message, "raw_modify_llm_output": None}
    
    # 检查必需的元数据是否存在 (上下文结果是可选的，没有它 LLM 也能尝试处理简单情况)
    if not all([schema, tables, sample]):
        error_msg = "解析修改请求失败：缺少数据库元数据 (Schema, Tables, Sample)。请确保初始化流程已成功运行。"
        logger.error(error_msg)
        return {"error_message": error_msg, "raw_modify_llm_output": None}

    try:
        # 调用 LLM 服务进行解析，传入上下文结果
        llm_output_str = llm_modify_service.parse_modify_request(
            query=query,
            schema_str=schema,
            table_names=tables,
            data_sample_str=sample,
            modify_context_result_str=context_result # 传递上下文结果
        )
        logger.info(f"LLM 解析原始输出 (带上下文): {llm_output_str}")

        # 检查 LLM 是否返回了空列表字符串或其他表示失败的标记
        if llm_output_str.strip() == '[]' or not llm_output_str.strip():
             # 如果 LLM 明确表示无法解析，则认为这不是一个运行时错误，而是一个需要用户澄清的情况
             clarification_msg = "抱歉，我无法完全理解您的修改请求。请提供更具体的信息，例如要修改哪个表、哪条记录（使用主键），以及要修改哪些字段和新值。"
             logger.info(clarification_msg)
             # 注意：这里我们不设置 error_message，而是设置 final_answer 让流程直接结束并回复用户
             # 这样做可以避免进入后续的错误处理流程，直接请求用户澄清
             return {"final_answer": clarification_msg, "raw_modify_llm_output": None}

        # 成功解析，存储原始 LLM 输出，清除错误信息
        return {"raw_modify_llm_output": llm_output_str, "error_message": None}

    except Exception as e:
        error_msg = f"调用 LLM 解析修改请求时发生错误: {e}"
        logger.error(error_msg)
        return {"error_message": error_msg, "raw_modify_llm_output": None}

def validate_and_store_modification_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：验证 LLM 输出的 JSON 格式，存储预览字符串 (`content_modify`)
              并解析/转换/存储 API 负载 (`lastest_content_production`)。
    对应 Dify Code 节点 '1742439839388' 的部分逻辑（简化版，仅做 JSON 格式校验）
    以及 Dify Assigner 节点 '1742440011915' 的逻辑。
    """
    logger.info("---节点: 验证并存储修改内容--- marginalised")
    raw_output = state.get("raw_modify_llm_output")
    error_message = state.get("error_message") # 保留上一步可能产生的错误

    # 如果上一步 LLM 调用就出错了，直接传递错误
    if error_message:
        logger.info(f"上一步骤存在错误: {error_message}")
        return {"error_message": error_message, "content_modify": None, "lastest_content_production": None}

    # 修改：如果 raw_output 为空或 '[]'，说明上一步已请求澄清，
    # 此节点不应设置错误，只需返回空字典让流程继续，保留上一步设置的 final_answer。
    if not raw_output or raw_output.strip() == '[]':
        logger.info("上一步骤未能解析出修改内容或请求了澄清，跳过验证和存储。")
        return {}

    try:
        # 尝试解析 JSON 以确保格式基本正确
        llm_parsed_data = json.loads(raw_output)
        logger.info("LLM 输出 JSON 格式有效。")

        # --- 新增：转换 LLM 输出为 API 负载格式 (List[Dict]) ---
        api_payload = []
        if isinstance(llm_parsed_data, dict):
            for table_name, operations in llm_parsed_data.items():
                if isinstance(operations, list):
                    for op in operations:
                        if isinstance(op, dict):
                            # 构建 API 期望的单条操作字典
                            single_op_payload = {
                                "table_name": table_name,
                                "primary_key": op.get("primary_key"),
                                "primary_value": op.get("primary_value"),
                                "target_primary_value": op.get("target_primary_value", ""), # 确保存在
                                "update_fields": op.get("fields", {}) # 确保存在
                            }
                            # 检查基本字段是否存在 (可选但推荐)
                            if single_op_payload["primary_key"] is not None and single_op_payload["primary_value"] is not None:
                                api_payload.append(single_op_payload)
                            else:
                                logger.warning(f"跳过格式不完整的修改操作（缺少主键信息）: {op}")
                        else:
                             logger.warning(f"LLM 输出中表 '{table_name}' 的操作项不是字典: {op}")
                else:
                     logger.warning(f"LLM 输出中表 '{table_name}' 的值不是列表: {operations}")
        else:
            raise ValueError("LLM 解析出的数据不是预期的字典格式。")
        
        if not api_payload:
             raise ValueError("未能从 LLM 输出中成功转换出任何有效的 API 修改操作。")
        
        logger.info(f"成功转换 API 负载: {api_payload}")
        # --- 转换结束 ---

        # 清空 save_content 确保后续确认流程干净
        # 清空 error_message 因为 JSON 格式有效且转换成功
        # 将原始有效的 JSON 字符串存入 content_modify (用于预览)
        # 将转换后的列表存入 lastest_content_production (用于 API 调用)
        return {
            "content_modify": raw_output, # 预览内容
            "lastest_content_production": api_payload, # API 负载
            "save_content": None,
            "error_message": None
        }

    except json.JSONDecodeError as e:
        error_msg = f"LLM 输出的修改内容无法解析为有效的 JSON: {e}"
        logger.error(error_msg)
        # 解析失败，设置错误信息，清空相关状态
        return {"error_message": error_msg, "content_modify": None, "lastest_content_production": None}
    except ValueError as e:
        # 捕获转换过程中可能抛出的 ValueError
        error_msg = f"转换 LLM 输出为 API 负载时出错: {e}"
        logger.error(error_msg)
        return {"error_message": error_msg, "content_modify": None, "lastest_content_production": None}
    except Exception as e:
        # 其他潜在错误
        error_msg = f"验证和存储修改内容时发生意外错误: {e}"
        logger.error(error_msg)
        return {"error_message": error_msg, "content_modify": None, "lastest_content_production": None}

def handle_modify_error_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：处理修改流程中发生的错误。
    """
    logger.info("---节点: 处理修改流程错误--- marginalised")
    error_message = state.get("error_message", "发生未知错误")

    # TODO (可选): 调用 LLM 服务 format_modify_error 来美化错误信息
    # formatted_error = llm_modify_service.format_modify_error(error_message)
    # final_answer = formatted_error

    final_answer = f"处理您的修改请求时遇到问题：\n{error_message}"

    return {"final_answer": final_answer}


def provide_modify_feedback_action(state: GraphState) -> Dict[str, Any]:
    """
    节点动作：向用户反馈已准备好的修改内容，并提示进行保存确认。
    对应 Dify Answer 节点: '1742440037542'
    """
    logger.info("---节点: 提供修改反馈--- marginalised")
    content_modify = state.get("content_modify", "[错误：未找到已准备的修改内容]")

    #TODO: 可以在这里添加对 content_modify 的美化逻辑，如果需要的话
    # formatted_content = _format_json_for_display(content_modify)

    final_answer = f"已准备好以下修改内容，请发送'保存'进行最终确认：\n\n{content_modify}"

    return {"final_answer": final_answer}


# 辅助函数 (示例，用于美化 JSON 显示，可以根据需要实现)
# def _format_json_for_display(json_str: Optional[str]) -> str:
#     if not json_str:
#         return ""
#     try:
#         data = json.loads(json_str)
#         # 这里可以实现更复杂的格式化逻辑，例如提取关键信息、使用 Markdown 等
#         return json.dumps(data, indent=2, ensure_ascii=False)
#     except:
#         return json_str # 解析失败则返回原始字符串


# 将在此处添加 handle_modify_error_action 函数

# 将在此处添加 provide_modify_feedback_action 函数 