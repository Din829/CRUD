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
    query = state.get("query", "")
    schema = state.get("biaojiegou_save", "{}")
    table_names = state.get("table_names", [])
    data_sample = state.get("data_sample", "{}")
    if not schema or schema == "{}" or not table_names:
        error_msg = "无法生成 SQL：缺少 Schema 或表名信息。"
        print(error_msg)
        return {"final_answer": error_msg, "sql_query_generated": None, "error_message": error_msg}
    try:
        generated_sql = llm_query_service.generate_select_sql(query, schema, table_names, data_sample)
        if generated_sql.startswith("ERROR:"):
            print(f"LLM 请求澄清 (SELECT): {generated_sql}")
            return {"final_answer": generated_sql, "sql_query_generated": None, "error_message": generated_sql}
        else:
            print(f"生成的 SELECT SQL: {generated_sql}")
            return {"sql_query_generated": generated_sql, "error_message": None}
    except Exception as e:
        error_msg = f"生成 SELECT SQL 时发生意外错误: {e}"
        print(error_msg)
        return {"final_answer": "抱歉，生成查询时遇到问题，请稍后重试或调整您的问题。", "sql_query_generated": None, "error_message": error_msg}

def generate_analysis_sql_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：调用 LLM 服务生成分析 SQL 查询。"""
    print("---节点: 生成分析 SQL---")
    query = state.get("query", "")
    schema = state.get("biaojiegou_save", "{}")
    table_names = state.get("table_names", [])
    data_sample = state.get("data_sample", "{}")
    if not schema or schema == "{}" or not table_names:
        error_msg = "无法生成分析 SQL：缺少 Schema 或表名信息。"
        print(error_msg)
        return {"final_answer": error_msg, "sql_query_generated": None, "error_message": error_msg}
    try:
        generated_sql = llm_query_service.generate_analysis_sql(query, schema, table_names, data_sample)
        if generated_sql.startswith("ERROR:"):
            print(f"LLM 请求澄清 (分析): {generated_sql}")
            return {"final_answer": generated_sql, "sql_query_generated": None, "error_message": generated_sql}
        else:
            print(f"生成的分析 SQL: {generated_sql}")
            return {"sql_query_generated": generated_sql, "error_message": None}
    except Exception as e:
        error_msg = f"生成分析 SQL 时发生意外错误: {e}"
        print(error_msg)
        return {"final_answer": "抱歉，生成分析查询时遇到问题，请稍后重试或调整您的问题。", "sql_query_generated": None, "error_message": error_msg}

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
        result_str = api_client.execute_query(sql_query)
        print(f"查询结果 (JSON string): {result_str}")
        return {"sql_result": result_str, "error_message": None, "final_answer": None}
    except Exception as e:
        error_msg = f"执行 SQL 查询时出错: {e}"
        print(error_msg)
        intent = state.get("query_analysis_intent", "query")
        clarify_msg = "请澄清你的分析需求。" if intent == "analysis" else "请澄清你的查询条件。"
        return {"sql_result": None, "error_message": error_msg, "final_answer": f"执行查询时遇到错误。{clarify_msg}"}

# --- 查询/分析流程 - 简单回复节点 ---

def handle_query_not_found_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理查询成功但结果为空的情况。"""
    print("---节点: 处理查询未找到---")
    return {"final_answer": "没有找到您想查找的数据，请尝试重新输入或提供更完整的编号。"}

def handle_analysis_no_data_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理分析成功但结果为空的情况。"""
    print("---节点: 处理分析无数据---")
    return {"final_answer": "根据您的条件分析，没有找到相关数据。"}

def handle_clarify_query_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理查询流程中需要用户澄清的情况。"""
    print("---节点: 请求澄清查询---")
    clarification_needed = state.get("final_answer", "请澄清你的查询条件，例如提供完整编号或指定具体字段。")
    return {"final_answer": clarification_needed}

def handle_clarify_analysis_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：处理分析流程中需要用户澄清的情况。"""
    print("---节点: 请求澄清分析---")
    clarification_needed = state.get("final_answer", "请澄清你的分析需求，例如'统计每个部门的员工数'。")
    return {"final_answer": clarification_needed}

# --- 查询/分析流程 - 结果处理节点 ---

def format_query_result_action(state: GraphState) -> Dict[str, Any]:
    """节点动作：调用 LLM 服务格式化查询结果。"""
    print("---节点: 格式化查询结果---")
    query = state.get("query", "")
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
    query = state.get("query", "")
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