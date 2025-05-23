# query_actions.py: 包含查询/分析流程相关的 LangGraph 动作节点函数。

import json
from typing import Dict, Any, List

# 导入状态定义、API 客户端、数据处理工具和 LLM 服务
from langgraph_crud_app.graph.state import GraphState
from langgraph_crud_app.services import api_client, data_processor
from langgraph_crud_app.services.llm import llm_query_service # 更新导入路径

# --- 查询/分析流程动作节点 ---

def generate_select_sql_action(state: GraphState) -> Dict[str, Any]:
    """
    动作节点：调用 LLM 服务生成 SELECT SQL 语句。
    对应 Dify 节点: '1742268678777'
    """
    print("---节点: 生成 SELECT SQL---")
    query = state.get("user_query", "")
    schema = state.get("biaojiegou_save", "{}")
    table_names = state.get("table_names", [])
    data_sample = state.get("data_sample", "{}")
    if not schema or schema == "{}" or not table_names:
        error_msg = "无法生成 SQL：缺少 Schema 或表名信息。"
        print(error_msg)
        return {"final_answer": error_msg, "sql_query_generated": None, "error_message": error_msg}
    try:
        generated_sql = llm_query_service.generate_select_sql(query, schema, table_names, data_sample)
        # 如果 LLM 返回的是错误或澄清请求
        if generated_sql.startswith("ERROR:") or generated_sql.startswith("CLARIFY:"):
            log_prefix = "LLM 返回错误" if generated_sql.startswith("ERROR:") else "LLM 请求澄清"
            print(f"{log_prefix} (SELECT): {generated_sql}")
            # 对于错误和澄清，都将原始消息设置到 final_answer, sql_query_generated (用于路由), 和 error_message
            # 并且对于澄清，也应该认为是某种形式的"流程未按预期完成"，因此设置 error_flag
            # 意图已被处理（即使结果是澄清）
            is_error = generated_sql.startswith("ERROR:")
            return {
                "final_answer": generated_sql,
                "sql_query_generated": generated_sql, # 路由会基于此判断是否澄清
                "error_message": generated_sql,
                "error_flag": True, # 无论是 ERROR 还是 CLARIFY，都认为是需要特殊处理的标志
                "current_intent_processed": True # 意图已处理
            }
        else:
            # 正常生成 SQL
            print(f"生成的 SELECT SQL: {generated_sql}")
            return {
                "sql_query_generated": generated_sql, 
                "error_message": None, 
                "current_intent_processed": True # 意图已处理
            }
    except Exception as e:
        error_msg = f"生成 SELECT SQL 时发生意外错误: {e}"
        print(error_msg)
        return {
            "final_answer": "抱歉，生成查询时遇到问题，请稍后重试或调整您的问题。", 
            "sql_query_generated": None, 
            "error_message": error_msg,
            "error_flag": True, # 标记错误
            "current_intent_processed": True # 意图已处理
        }

def generate_analysis_sql_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：调用 LLM 服务生成分析 SQL 查询。"""
    print("---节点: 生成分析 SQL---")
    query = state.get("user_query", "")
    schema = state.get("biaojiegou_save", "{}")
    table_names = state.get("table_names", [])
    data_sample = state.get("data_sample", "{}")
    if not schema or schema == "{}" or not table_names:
        error_msg = "无法生成分析 SQL：缺少 Schema 或表名信息。"
        print(error_msg)
        return {
            "final_answer": error_msg, 
            "sql_query_generated": None, 
            "error_message": error_msg,
            "error_flag": True,
            "current_intent_processed": True
        }
    try:
        generated_sql = llm_query_service.generate_analysis_sql(query, schema, table_names, data_sample)
        if generated_sql.startswith("ERROR:"):
            print(f"LLM 返回错误 (分析): {generated_sql}") # Log 统一为 LLM 返回错误
            return {
                "final_answer": generated_sql, 
                "sql_query_generated": None, 
                "error_message": generated_sql,
                "error_flag": True,
                "current_intent_processed": True
            }
        # 假设分析SQL也可能返回 CLARIFY: (保持与 select 一致性)
        elif generated_sql.startswith("CLARIFY:"):
            print(f"LLM 请求澄清 (分析): {generated_sql}")
            return {
                "final_answer": generated_sql,
                "sql_query_generated": generated_sql, # 澄清时 SQL query generated 包含澄清消息
                "error_message": generated_sql,
                "error_flag": True, # 澄清也标记为 error_flag True
                "current_intent_processed": True
            }
        else:
            print(f"生成的分析 SQL: {generated_sql}")
            return {
                "sql_query_generated": generated_sql, 
                "error_message": None,
                "current_intent_processed": True
            }
    except Exception as e:
        error_msg = f"生成分析 SQL 时发生意外错误: {e}"
        print(error_msg)
        return {
            "final_answer": "抱歉，生成分析查询时遇到问题，请稍后重试或调整您的问题。", 
            "sql_query_generated": None, 
            "error_message": error_msg,
            "error_flag": True,
            "current_intent_processed": True
        }

def clean_sql_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：清理生成的 SQL 语句。"""
    print("---节点: 清理 SQL---")
    raw_sql = state.get("sql_query_generated")
    if not raw_sql or raw_sql.startswith("ERROR:"):
        print("没有有效的 SQL 需要清理，跳过。")
        return {}
    cleaned_sql = data_processor.clean_sql_string(raw_sql)
    print(f"清理后的 SQL: {cleaned_sql}")
    return {"sql_query_generated": cleaned_sql}

def execute_sql_query_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：执行清理后的 SQL 查询。"""
    print("---节点: 执行 SQL 查询---")
    sql_query = state.get("sql_query_generated")
    if not sql_query or sql_query.startswith("ERROR:"):
        error_msg = "没有有效的 SQL 语句可执行。"
        print(error_msg)
        return {"final_answer": state.get("final_answer", "无法执行查询。"), "sql_result": None, "error_message": error_msg}
    try:
        print(f"执行 SQL: {sql_query}")
        # api_client.execute_query 预期返回 Python 对象 (例如 list of dicts)
        result_obj = api_client.execute_query(sql_query)
        # 将 Python 对象转换为 JSON 字符串以存入 GraphState
        result_str = json.dumps(result_obj)
        print(f"查询结果 (Python object): {result_obj}") # 日志中保留原始对象以便观察
        print(f"查询结果 (JSON string for state): {result_str}")
        return {"sql_result": result_str, "error_message": None, "final_answer": None}
    except Exception as e:
        error_msg = f"执行 SQL 查询时出错: {e}"
        print(error_msg)
        
        # 尝试使用LLM错误服务转换错误
        try:
            from langgraph_crud_app.services.llm import llm_error_service
            
            operation_context = {
                "user_query": state.get("user_query", "未知查询"),
                "operation_type": "查询"
            }
            
            friendly_error = llm_error_service.translate_flask_error(
                error_info=str(e),
                operation_context=operation_context
            )
            
            return {"sql_result": None, "error_message": error_msg, "final_answer": friendly_error}
            
        except Exception as llm_error:
            print(f"LLM错误转换失败: {llm_error}")
            # 回退到原来的处理方式
            intent = state.get("query_analysis_intent", "query")
            clarify_msg = "请澄清你的分析需求。" if intent == "analysis" else "请澄清你的查询条件。"
            return {"sql_result": None, "error_message": error_msg, "final_answer": f"执行查询时遇到错误。{clarify_msg}"}

# --- 查询/分析流程 - 简单回复节点 ---

def handle_query_not_found_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理查询成功但结果为空的情况。"""
    print("---节点: 处理查询未找到---")
    return {
        "final_answer": "没有找到您想查找的数据，请尝试重新输入或提供更完整的编号。",
        "error_flag": True,  # 标记为一种"非成功"状态，即使不是严格的执行错误
        "error_message": "查询成功，但未找到匹配数据。" # 提供一个内部的错误/状态信息
    }

def handle_analysis_no_data_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理分析成功但结果为空的情况。"""
    print("---节点: 处理分析无数据---")
    return {"final_answer": "根据您的条件分析，没有找到相关数据。"}

def handle_clarify_query_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理查询流程中需要用户澄清的情况。"""
    print("---节点: 请求澄清查询---")
    current_final_answer = state.get("final_answer")
    print(f"DEBUG: handle_clarify_query_action - current_final_answer from state: {current_final_answer}")
    default_clarification = "请澄清你的查询条件，例如提供完整编号或指定具体字段。"
    clarification_needed = current_final_answer if current_final_answer is not None else default_clarification
    print(f"DEBUG: handle_clarify_query_action - clarification_needed set to: {clarification_needed}")
    # 关键修正: 确保澄清节点也传递意图已处理的状态
    return {
        "final_answer": clarification_needed, 
        "current_intent_processed": True,
        "debug_clarify_node_executed": "YES_QUERY"
    }

def handle_clarify_analysis_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理分析流程中需要用户澄清的情况。"""
    print("---节点: 请求澄清分析---")
    clarification_needed = state.get("final_answer", "请澄清你的分析需求，例如'统计每个部门的员工数'。")
    # 关键修正: 确保澄清节点也传递意图已处理的状态
    return {"final_answer": clarification_needed, "current_intent_processed": True}

# --- 查询/分析流程 - 结果处理节点 ---

def format_query_result_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：调用 LLM 服务格式化查询结果。"""
    print("---节点: 格式化查询结果---")
    query = state.get("user_query", "")
    sql_result = state.get("sql_result", "[]")
    try:
        formatted_answer = llm_query_service.format_query_result(query, sql_result)
        return {"final_answer": formatted_answer}
    except Exception as e:
        error_msg = f"格式化查询结果时出错: {e}"
        print(error_msg)
        return {"final_answer": f"查询结果格式化失败。原始结果: {sql_result}", "error_message": error_msg}

def analyze_analysis_result_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：调用 LLM 服务分析分析结果。"""
    print("---节点: 分析分析结果---")
    query = state.get("user_query", "")
    sql_result = state.get("sql_result", "[]")
    schema = state.get("biaojiegou_save", "{}")
    table_names = state.get("table_names", [])
    try:
        analysis_report = llm_query_service.analyze_analysis_result(query, sql_result, schema, table_names)
        return {"final_answer": analysis_report}
    except Exception as e:
        error_msg = f"分析分析结果时出错: {e}"
        print(error_msg)
        return {"final_answer": f"分析结果生成报告失败。原始结果: {sql_result}", "error_message": error_msg} 