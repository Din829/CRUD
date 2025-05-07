from typing import Dict, Any, Optional
import re

from langgraph_crud_app.graph.state import GraphState
# 确保导入 llm_delete_service, api_client, data_processor
from langgraph_crud_app.services.llm import llm_delete_service
from langgraph_crud_app.services import api_client
from langgraph_crud_app.services import data_processor

def generate_delete_preview_sql_action(state: GraphState) -> Dict[str, Any]:
    """动作节点：生成用于预览待删除记录的 SELECT SQL。"""
    print("--- 动作: 生成删除预览 SQL ---")
    error_key = "delete_error_message" # 统一使用 delete 流程的错误 key
    final_answer_update = {}

    try:
        user_query = state["user_query"]
        schema_info = state["biaojiegou_save"]
        table_names = state["table_names"]
        sample_data = state["data_sample"]

        if not all([user_query, schema_info, table_names, sample_data]):
            missing = [k for k, v in {"user_query": user_query, "schema_info": schema_info, "table_names": table_names, "sample_data": sample_data}.items() if not v]
            raise ValueError(f"缺少必要信息: {', '.join(missing)}")

        # 不再强制简化SQL
        sql_output = llm_delete_service.generate_delete_preview_sql(
            user_query=user_query,
            schema_info=schema_info,
            table_names=table_names,
            sample_data=sample_data
        )

        # 检查 LLM 是否返回了提示而非 SQL
        if sql_output.startswith("请提供有效") or sql_output.startswith("错误："):
            print(f"--- LLM 返回提示或错误: {sql_output} ---")
            final_answer_update = {"final_answer": sql_output}
            # 返回错误，中断后续流程，但不设置 delete_error_message，因为这是正常提示
            # 需要一种方式告诉路由停止，这里通过 final_answer 间接实现
            return {error_key: None, "delete_preview_sql": None, **final_answer_update}

        # SQL完整性检查
        if not data_processor.is_sql_part_balanced(sql_output):
            print("--- 警告: 生成的SQL括号不平衡 ---")
            error_msg = "生成的SQL括号不匹配，请重试"
            return {error_key: error_msg, "delete_preview_sql": None}

        # 成功生成 SQL
        print(f"--- 成功生成预览 SQL ---")
        return {error_key: None, "delete_preview_sql": sql_output, **final_answer_update}

    except Exception as e:
        print(f"ERROR in generate_delete_preview_sql_action: {e}")
        error_msg = f"生成删除预览 SQL 时出错: {e}"
        return {error_key: error_msg, "delete_preview_sql": None, **final_answer_update}


def clean_delete_sql_action(state: GraphState) -> Dict[str, Any]:
    """动作节点：清理 LLM 生成的删除预览 SQL。"""
    print("--- 动作: 清理删除预览 SQL ---")
    error_key = "delete_error_message"
    if state.get(error_key): # 检查上一步是否有错误
        print("--- 跳过清理 SQL，因存在错误 ---")
        return {}
    if not state.get("delete_preview_sql"): # 检查上一步是否生成了 SQL (可能返回了提示)
        print("--- 跳过清理 SQL，无 SQL 可清理 ---")
        return {}

    try:
        sql_to_clean = state["delete_preview_sql"]
        print(f"--- 原始SQL (长度: {len(sql_to_clean)}): {sql_to_clean[:100]}... ---")
        
        # 基本清理
        cleaned_sql = data_processor.clean_sql_string(sql_to_clean)
        
        # 额外的MySQL语法错误预防措施
        # 1. 移除所有尾部分号（API会自动添加）
        cleaned_sql = cleaned_sql.strip()
        while cleaned_sql.endswith(';'):
            cleaned_sql = cleaned_sql[:-1].strip()
            
        # 2. 检查SQL是否为空
        if not cleaned_sql:
            print("--- 警告: 清理后的SQL为空 ---")
            error_msg = "清理后的SQL语句为空，无法执行查询"
            return {error_key: error_msg, "delete_preview_sql": None}
            
        # 3. 确保是SELECT语句
        if not cleaned_sql.upper().startswith("SELECT"):
            print(f"--- 警告: 清理后的SQL不是SELECT语句: {cleaned_sql[:100]}... ---")
            error_msg = f"生成的SQL不是SELECT语句，无法安全执行: {cleaned_sql[:100]}..."
            return {error_key: error_msg, "delete_preview_sql": None}
        
        # 4. 复杂查询检查: 确保UNION ALL语句完整
        if " UNION ALL " in cleaned_sql.upper():
            parts = cleaned_sql.upper().split(" UNION ALL ")
            for i, part in enumerate(parts):
                if not part.strip().startswith("SELECT"):
                    print(f"--- 警告: UNION ALL部分{i+1}不是有效的SELECT语句 ---")
                    if i > 0:  # 如果不是第一部分，可能是被截断了
                        print("--- 尝试修复: 截断到前一个完整的UNION ALL部分 ---")
                        cleaned_sql = " UNION ALL ".join(parts[:i])
                        print(f"--- 修复后的SQL (长度: {len(cleaned_sql)}): {cleaned_sql[:100]}... ---")
                        break
        
        # 5. 检查SQL是否被截断，特别关注WHERE子句
        # where_match = re.search(r'\bWHERE\b\s+([^)]{1,50})$', cleaned_sql, re.IGNORECASE)
        # if where_match:
        #     print(f"--- 警告: SQL可能在WHERE子句处被截断: '{where_match.group(0)}' ---")
        #     error_msg = "SQL语句似乎被截断，请简化查询条件"
        #     return {error_key: error_msg, "delete_preview_sql": None}
            
        # 6. 括号平衡检查
        if not data_processor.is_sql_part_balanced(cleaned_sql):
            print("--- 警告: SQL括号不平衡，可能被截断 ---")
            error_msg = "SQL语句括号不匹配，可能结构不完整"
            return {error_key: error_msg, "delete_preview_sql": None}
        
        # 记录完整的清理后SQL，不截断
        print(f"--- SQL清理完成，长度: {len(cleaned_sql)} ---")
        print("--- 清理后SQL的前100个字符: " + cleaned_sql[:100] + "... ---")
        print("--- 清理后SQL的最后100个字符: ..." + cleaned_sql[-100:] + " ---")
        
        return {error_key: None, "delete_preview_sql": cleaned_sql}
    except Exception as e:
        print(f"ERROR in clean_delete_sql_action: {e}")
        error_msg = f"清理删除预览 SQL 时出错: {e}"
        return {error_key: error_msg}


def execute_delete_preview_sql_action(state: GraphState) -> Dict[str, Any]:
    """动作节点：执行预览 SQL 查询待删除的记录。"""
    print("--- 动作: 执行删除预览 SQL ---")
    error_key = "delete_error_message"
    if state.get(error_key):
        print("--- 跳过执行预览 SQL，因存在错误 ---")
        return {}
    if not state.get("delete_preview_sql"):
        print("--- 跳过执行预览 SQL，无 SQL 可执行 ---")
        return {}

    try:
        sql_query = state["delete_preview_sql"]
        
        # 执行SQL前的额外安全检查
        if not sql_query or sql_query.isspace():
            print("--- SQL为空，无法执行 ---")
            return {error_key: "生成的SQL查询为空，无法执行"}
            
        if not sql_query.upper().startswith("SELECT"):
            print(f"--- SQL不是SELECT语句: {sql_query} ---")
            return {error_key: f"生成的SQL不是SELECT语句，无法安全执行: {sql_query}"}
            
        print(f"--- 执行 SQL: {sql_query} ---")
        
        try:
            result_json_str = api_client.execute_query(sql_query)
            print(f"--- 预览查询结果 (JSON): {result_json_str} ---")
        except Exception as sql_error:
            # 处理SQL执行错误
            error_message = str(sql_error)
            print(f"--- SQL执行失败: {error_message} ---")
            
            # 根据错误类型提供更友好的错误消息
            if "1064" in error_message:  # MySQL语法错误代码
                return {error_key: f"SQL语法错误，请尝试简化查询条件: {error_message}"}
            elif "does not exist" in error_message.lower() or "unknown" in error_message.lower():
                return {error_key: f"查询引用了不存在的表或字段: {error_message}"}
            else:
                return {error_key: f"执行查询时出错: {error_message}"}
        
        # 检查结果是否为空列表
        if result_json_str.strip() == '[]':
            print("--- 查询结果为空列表，将继续流程但标记未找到记录 ---")
            # 更新状态以确保下游格式化步骤可以正确处理空结果
            return {
                error_key: None, 
                "delete_show": result_json_str,
                "delete_preview_text": "未找到需要删除的记录。", 
                "content_delete": "未找到需要删除的记录。" 
            }
            
        # 正常非空结果
        return {error_key: None, "delete_show": result_json_str}

    except Exception as e:
        print(f"ERROR in execute_delete_preview_sql_action: {e}")
        error_msg = f"执行删除预览查询失败: {e}"
        # API 错误时，设置错误消息，并将 delete_show 设为 None
        return {error_key: error_msg, "delete_show": None}


def format_delete_preview_action(state: GraphState) -> Dict[str, Any]:
    """动作节点：调用 LLM 格式化删除预览文本。"""
    print("--- 动作: 格式化删除预览 ---")
    error_key = "delete_error_message"
    
    # 如果已经在执行预览SQL步骤设置了删除预览文本（通常是未找到记录的情况），则直接使用
    if state.get("delete_preview_text") == "未找到需要删除的记录。":
        print("--- 使用已设置的'未找到记录'预览文本 ---")
        return {
            error_key: None,
            "delete_preview_text": "未找到需要删除的记录。",
            "content_delete": "未找到需要删除的记录。"
        }
    
    if state.get(error_key):
        print("--- 跳过格式化预览，因存在错误 ---")
        return {}
        
    # 检查 delete_show 是否存在且有效 (可能 API 调用失败返回 None)
    delete_show_json = state.get("delete_show")
    if delete_show_json is None:
        print("--- 跳过格式化预览，无预览数据 (delete_show is None) ---")
        # 可能之前的 API 调用失败了，错误已记录
        return {}

    # 检查是否为空JSON数组
    if delete_show_json.strip() == '[]':
        print("--- 预览数据为空数组，设置'未找到记录'消息 ---")
        return {
            error_key: None,
            "delete_preview_text": "未找到需要删除的记录。",
            "content_delete": "未找到需要删除的记录。"
        }

    try:
        schema_info = state["biaojiegou_save"]
        if not schema_info:
            raise ValueError("缺少 Schema 信息 (biaojiegou_save)")

        # 调用 LLM 服务进行格式化
        preview_text = llm_delete_service.format_delete_preview(
            delete_show_json=delete_show_json,
            schema_info=schema_info
        )

        # 如果 LLM 返回提示"未找到记录"，也要更新状态
        if preview_text == "未找到需要删除的记录。":
             print("--- LLM 确认未找到记录 ---")
             return {
                 error_key: None,
                 "delete_preview_text": preview_text,
                 "content_delete": preview_text # 也更新暂存区
             }

        print(f"--- 成功格式化预览文本 ---")
        # 同时更新预览文本和用于确认流程的暂存文本
        return {
            error_key: None,
            "delete_preview_text": preview_text,
            "content_delete": preview_text
        }

    except Exception as e:
        print(f"ERROR in format_delete_preview_action: {e}")
        error_msg = f"格式化删除预览时出错: {e}"
        # 尝试提供一个回退预览
        fallback_preview = f"无法生成格式化预览 ({e})。原始预览数据 (JSON):\n{delete_show_json}"
        return {
            error_key: error_msg,
            "delete_preview_text": fallback_preview,
            "content_delete": fallback_preview # 错误时也暂存回退信息
        }


def provide_delete_feedback_action(state: GraphState) -> Dict[str, Any]:
    """动作节点：向用户提供删除预览或错误信息。"""
    print("--- 动作: 提供删除反馈 ---")
    error_message = state.get("delete_error_message")
    preview_text = state.get("delete_preview_text")
    final_answer_value = ""

    if error_message:
        final_answer_value = f"处理删除请求时遇到问题：\n{error_message}"
        # 如果有错误，但仍生成了预览（可能是回退预览），附加它
        if preview_text:
            final_answer_value += f"\n\n参考信息：\n{preview_text}"
    elif preview_text:
        if preview_text == "未找到需要删除的记录。":
            final_answer_value = preview_text # 直接显示未找到
        else:
            # 成功生成预览，请求确认
            final_answer_value = f"{preview_text}\n\n请输入 '保存' 以继续删除流程，或输入 '重置' 取消。"
    else:
        # 理论上不应发生，除非流程逻辑错误
        final_answer_value = "抱歉，处理您的删除请求时发生未知错误。"

    return {"final_answer": final_answer_value}


def handle_delete_error_action(state: GraphState) -> Dict[str, Any]:
    """动作节点：处理删除流程中的通用错误。"""
    print("--- 动作: 处理删除流程错误 ---")
    # 这个节点主要用于路由，实际的错误信息应该已经在 provide_delete_feedback_action 中准备好了
    # 可以在这里记录详细错误日志或设置错误标志
    error_message = state.get("delete_error_message") or "删除流程发生未知错误。"
    print(f"捕获到删除流程错误: {error_message}")
    return {"error_flag": True} # 设置错误标志


def finalize_delete_response(state: GraphState) -> Dict[str, Any]:
    """空节点，确保删除流程反馈节点的输出被合并到最终状态。"""
    print("--- 节点: 结束删除反馈流程 ---")
    # 无需操作，仅用于图连接
    return {} 