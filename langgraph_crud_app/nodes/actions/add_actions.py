import json
from typing import Dict, Any

from langgraph_crud_app.graph.state import GraphState
from langgraph_crud_app.services import llm_add_service, data_processor
# from langgraph_crud_app.services import api_client # data_processor 内部会导入和使用

def parse_add_request_action(state: GraphState) -> Dict[str, Any]:
    """动作节点：使用 LLM 解析用户的新增请求。"""
    print("--- 动作: 解析新增请求 ---")
    try:
        user_query = state["user_query"]
        schema_info = state["biaojiegou_save"]
        sample_data = state["data_sample"]

        if not user_query or not schema_info or not sample_data:
            missing = []
            if not user_query: missing.append("用户查询(user_query)")
            if not schema_info: missing.append("Schema信息(biaojiegou_save)")
            if not sample_data: missing.append("示例数据(data_sample)")
            raise ValueError(f"解析新增请求缺少必要信息: {', '.join(missing)}。")

        llm_output = llm_add_service.parse_add_request(
            user_query=user_query,
            schema_info=schema_info,
            sample_data=sample_data
        )

        if not llm_output:
            raise ValueError(f"LLM 未能从用户输入中解析出有效的新增数据。")

        # 成功路径: 只返回 temp_add_llm_data
        return {"temp_add_llm_data": llm_output}

    except Exception as e:
        print(f"ERROR in parse_add_request_action: {e}")
        # 错误路径: 只返回更新
        # 将 temp_add_llm_data 设为 None
        updates = {"add_parse_error": str(e), "temp_add_llm_data": None}
        return updates

def process_add_llm_output_action(state: GraphState) -> Dict[str, Any]:
    """动作节点：清理和结构化新增请求的原始 LLM 输出。"""
    print("--- 动作: 处理新增 LLM 输出 ---")
    # 使用新的键名读取状态
    raw_output = state.get("temp_add_llm_data")
    # 如果上一步解析失败，直接返回
    if state.get("add_parse_error"):
        print("--- 跳过处理 LLM 输出，因为上一步解析失败 ---")
        return {}
    if not raw_output:
        print("警告：没有原始 LLM 输出可供处理，但上一步未报告错误。")
        # 将其视为一种错误状态
        return {"add_error_message": "无法处理空的 LLM 输出。"}

    try:
        # 调用 data_processor 进行清理和结构化
        structured_records = data_processor.clean_and_structure_llm_add_output(raw_output)
        if structured_records is None:
             raise ValueError("清理和结构化 LLM 输出返回 None。")

        # 将结构化记录序列化为 JSON 字符串
        try:
            records_json_str = json.dumps(structured_records, ensure_ascii=False)
        except TypeError as te:
            raise ValueError(f"无法将结构化记录序列化为 JSON: {te}")

        print(f"--- 结构化记录 (JSON String): {records_json_str} ---")
        # 将 JSON 字符串存入 state，清除旧错误
        return {"add_structured_records_str": records_json_str, "add_error_message": None}

    except ValueError as ve:
         print(f"ERROR in process_add_llm_output_action (ValueError): {ve}")
         # 出错时，清空字符串状态
         return {"add_error_message": str(ve), "add_structured_records_str": None} 
    except Exception as e:
        print(f"ERROR in process_add_llm_output_action: {e}")
        # 出错时，清空字符串状态
        return {"add_error_message": f"处理LLM输出失败: {str(e)}", "add_structured_records_str": None} 

def process_placeholders_action(state: GraphState) -> Dict[str, Any]:
    """
    动作节点：处理结构化记录中的 {{...}} 占位符。
    调用 data_processor.process_placeholders。

    Args:
        state: 当前图状态。

    Returns:
        包含处理后记录的字典。
    """
    print("--- 节点: 处理占位符 ({{...}} format) ---")
    # --- 新增：打印完整状态 --- 
    print(f"节点入口接收到的完整状态: {state}")
    # --- END 新增 ---
    
    # 检查前序步骤是否有错误
    if state.get("add_parse_error") or state.get("add_error_message"):
        print("--- 跳过处理占位符，因为前序步骤出错 ---")
        return {}

    # 读取 JSON 字符串状态
    records_json_str = state.get("add_structured_records_str")
    
    # structured_records = state.get("add_structured_records") # 不再直接读取这个

    structured_records = None # 初始化
    if records_json_str:
        try:
            structured_records = json.loads(records_json_str)
            if not isinstance(structured_records, list):
                raise ValueError("解析后的结构化记录不是列表。")
            print(f"--- 从 JSON 字符串成功解析结构化记录: {structured_records} ---")
        except json.JSONDecodeError as e:
            print(f"--- 无法解析结构化记录 JSON 字符串: {e} --- JSON: '{records_json_str}'")
            return {"add_error_message": f"无法解析结构化记录 JSON 字符串: {e}"}
        except ValueError as ve:
             print(f"--- 解析后的结构化记录格式错误: {ve} --- JSON: '{records_json_str}'")
             return {"add_error_message": f"解析后的结构化记录格式错误: {ve}"}
    
    # 检查解析结果或原始字符串是否存在
    if structured_records is None:
         print("--- 无法处理占位符：结构化记录 JSON 字符串为空或解析失败 ---")
         # 如果 records_json_str 为空，之前的步骤就应该设置 error_message 了
         # 如果解析失败，上面已经返回了错误
         # 这里理论上不应该到达，除非 state 被意外修改
         return {"add_error_message": "结构化记录丢失或无效，无法处理占位符。"}
    elif not structured_records: # 列表为空的情况
         print("--- 无结构化记录需要处理占位符 (列表为空) ---")
         return {"add_processed_records": []}

    print(f"--- 待处理占位符的记录: {structured_records} ---")

    try:
        # 调用 data_processor 处理占位符 (现在使用解析后的 structured_records)
        processed_records = data_processor.process_placeholders(structured_records)
        print(f"--- 占位符处理完成: {processed_records} ---")

        # 将最终处理后的记录序列化为 JSON 字符串并存入状态
        try:
            processed_records_json_str = json.dumps(processed_records, ensure_ascii=False)
        except TypeError as te:
            raise ValueError(f"无法将处理后的记录序列化为 JSON: {te}")
        
        # 更新 _str 字段，清除错误
        return {"add_processed_records_str": processed_records_json_str, "add_error_message": None}

    except ValueError as ve: 
        print(f"ERROR in process_placeholders_action (ValueError): {ve}")
        # 出错时，清空字符串状态
        return {"add_error_message": str(ve), "add_processed_records_str": None} 
    except Exception as e:
        print(f"ERROR in process_placeholders_action: {e}")
        # 出错时，清空字符串状态
        return {"add_error_message": f"处理占位符时发生意外错误: {str(e)}", "add_processed_records_str": None} 

def format_add_preview_action(state: GraphState) -> Dict[str, Any]:
    """
    调用 LLM 生成新增数据的预览文本。

    Args:
        state: 当前图状态。

    Returns:
        一个字典，包含生成的预览文本。
    """
    print("--- 节点: 格式化新增预览文本 ---")
    # 检查前序步骤是否有错误
    current_error = state.get("add_parse_error") or state.get("add_error_message")
    if current_error:
        print(f"--- 跳过格式化预览，因为前序步骤出错: {current_error} ---")
        return {} 

    # 从 _str 字段读取状态
    processed_records_json_str = state.get("add_processed_records_str")
    # processed_records = state.get("add_processed_records") # 不再直接读取

    processed_records = None # 初始化
    if processed_records_json_str:
        try:
            processed_records = json.loads(processed_records_json_str)
            if not isinstance(processed_records, list):
                 raise ValueError("解析后的已处理记录不是列表。")
            print(f"--- 从 JSON 字符串成功解析已处理记录: {processed_records} ---")
        except json.JSONDecodeError as e:
            print(f"--- 无法解析已处理记录 JSON 字符串: {e} --- JSON: '{processed_records_json_str}'")
            return {"add_error_message": f"无法解析已处理记录 JSON 字符串: {e}"} 
        except ValueError as ve:
            print(f"--- 解析后的已处理记录格式错误: {ve} --- JSON: '{processed_records_json_str}'")
            return {"add_error_message": f"解析后的已处理记录格式错误: {ve}"} 
    
    # 检查解析结果
    if processed_records is None:
         print(f"--- 无法生成预览：已处理记录 JSON 字符串为空或解析失败 ---")
         return {"add_error_message": "已处理记录丢失或无效，无法生成预览。"}
    elif not processed_records: 
         print("--- 没有处理后的记录可供预览 (列表为空) ---")
         return {"add_preview_text": "根据您的输入，没有解析到需要新增的数据。"}

    # --- 后续逻辑使用解析后的 processed_records --- 
    query = state["user_query"]
    # schema = state["db_schema"] # db_schema 似乎未在 state 中定义，暂时使用 biaojiegou_save
    schema_str = state.get("biaojiegou_save")
    if not schema_str:
         print("--- 无法生成预览：数据库 Schema 信息丢失。 ---")
         return {"add_error_message": "数据库 Schema 信息丢失，无法生成预览。"}

    # 从处理后的记录中提取涉及的表名
    involved_tables = list(set(record.get("table_name", "unknown") for record in processed_records))

    print(f"--- 格式化预览输入 - Tables: {involved_tables}, Records: {processed_records} ---")

    # 调用 LLM 服务生成预览 (使用解析后的 processed_records)
    try:
        records_by_table = {} 
        for record in processed_records:
            table_name = record.get("table_name")
            if table_name:
                if table_name not in records_by_table:
                    records_by_table[table_name] = []
                records_by_table[table_name].append(record.get("fields", {}))

        if not records_by_table:
             print("--- 警告：处理后的记录无法按表分组进行预览 ---")
             # 提供基于原始列表的预览
             preview_text = f"准备新增以下记录（无法按表分组）：\n{json.dumps(processed_records, ensure_ascii=False, indent=2)}"
        else:
            preview_text = llm_add_service.format_add_preview(
               query=query,
               schema=schema_str, # 使用 schema_str
               table_names=list(records_by_table.keys()),
               processed_records=records_by_table 
            )

        # 存储预览文本到 add_preview_text 和 content_new，同时存储处理后的数据到 lastest_content_production
        return {
            "add_preview_text": preview_text,
            "content_new": preview_text, # 同时更新 content_new
            "lastest_content_production": processed_records, # 同时更新 lastest_content_production
            "add_error_message": None
        }
    except Exception as e:
        print(f"--- 调用 format_add_preview 时出错: {e} ---")
        # 出错时，也要确保存储了回退预览文本，并清空 content_new 和 lastest_content_production
        try:
             fallback_preview = f"无法生成格式化预览 ({e})。将尝试新增以下数据：\n{json.dumps(processed_records, ensure_ascii=False, indent=2)}"
        except Exception:
             fallback_preview = f"无法生成格式化预览 ({e}) 且无法显示待新增数据。"
        return {
            "add_error_message": f"生成预览文本时出错: {e}",
            "add_preview_text": fallback_preview,
            "content_new": None, # 出错时清空 content_new
            "lastest_content_production": None # <--- 新增此行
        }


def provide_add_feedback_action(state: GraphState) -> Dict[str, Any]:
    """动作节点：向用户提供生成的新增预览或错误信息。"""
    print("--- 动作: 提供新增反馈 ---")
    # 检查所有可能的错误状态
    parse_error = state.get("add_parse_error") 
    processing_error = state.get("add_error_message")
    preview = state.get("add_preview_text")

    final_answer_value = ""
    if parse_error:
        final_answer_value = f"抱歉，无法解析您的新增请求：\n{parse_error}"
    elif processing_error:
        final_answer_value = f"抱歉，处理您的新增请求时出错：\n{processing_error}"
        if preview: 
             final_answer_value += f"\n\n预览（可能有误）：\n{preview}"
    elif preview:
        final_answer_value = f"{preview}\n\n请输入 '保存' 以确认新增，或输入 '重置' 取消。"
    else:
        final_answer_value = "抱歉，发生了未知错误，无法处理您的请求。"

    # 返回到 final_answer 键，供 main.py 读取
    return {"final_answer": final_answer_value}

def handle_add_error_action(state: GraphState) -> Dict[str, Any]:
    """处理新增工作流特有的错误 (通用错误节点)。"""
    print("--- 动作: 处理新增错误 (通用) ---")
    error_message = state.get("add_error_message") or state.get("add_parse_error") or "新增流程发生未知错误。"
    # 这个节点通常在路由判定为错误时进入
    # provide_add_feedback_action 已经格式化了错误信息
    # 这里可以只记录日志，或者返回一个更通用的错误
    # return {"final_answer": f"新增操作失败：{error_message}"}
    # 通常错误信息已通过 provide_add_feedback_action 的 final_answer 发送
    # 这里返回空或特定错误标志即可
    return {"error_flag": True} # 指示流程出错结束

# --- 新增：用于确保 final_answer 被包含在最终状态的节点 ---
def finalize_add_response(state: GraphState) -> Dict[str, Any]:
    """空节点，确保 provide_add_feedback 的输出被合并到最终状态。"""
    print("--- 节点: 结束新增反馈流程 ---")
    # 这个节点本身不需要做任何事情或返回任何更新
    return {}

