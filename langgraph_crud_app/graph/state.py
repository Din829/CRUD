# state.py: 定义 LangGraph 应用的状态 TypedDict。

from typing import List, TypedDict, Optional, Any, Dict
# 尝试从 typing_extensions 导入
try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired

class GraphState(TypedDict):
    """
    表示 LangGraph 应用的状态，映射 Dify 的 conversation 变量并包含必要的工作流字段。
    """
    # --- 核心 Dify conversation 变量 (镜像) ---
    biaojiegou_save: Optional[str]       # 格式化后的 Schema JSON 字符串 (来自 Dify 节点 '1742268574820')
    table_names: Optional[List[str]]     # 从 Schema 中提取的表名列表 (来自 Dify 节点 '1743382507830')
    data_sample: Optional[str]           # 数据示例 JSON 字符串 (来自 Dify 节点 '1742695585674')
    content_modify: Optional[str] = None  # 面向用户的修改操作预览内容 (由 LLM 生成，保存以供确认)
    content_new: Optional[str] = None     # 面向用户的创建操作预览内容 (由 LLM 生成，保存以供确认)
    delete_show: Optional[str] = None     # 面向用户的删除操作预览内容 (查询结果，保存以供确认)
    lastest_content_production: Optional[List[Dict[str, Any]]] = None # 修改类型！存储待提交API的创建/更新负载 (Python列表)
    delete_array: Optional[List[str]] = None    # 删除 API 调用的原始结构化负载 (JSON 字符串列表) (确认前准备)
    save_content: Optional[str] = None          # 控制标志，指示待处理的保存操作: "修改路径", "新增路径", "删除路径", "复合路径", 或 None (请求用户确认前设置)
    # id_check: Optional[str]            # Dify 变量，用途不明确，暂时省略，除非需要

    # 新增：用于存储 API 调用结果的临时字段
    api_call_result: Optional[str] = None       # 存储 /update_record, /insert_record, /delete_record 等 API 调用的返回结果

    # --- 工作流输入 / 输出 ---
    # query: str                           # 用户的输入查询 (来自 Dify 'sys.query')
    user_query: str                      # 用户的输入查询 (修正键名)
    final_answer: Optional[str]          # 给用户的最终回复 (由 Dify 中的 Answer 节点生成)
    error_message: Optional[str]         # 存储执行期间的错误信息 (捕获来自 Code 节点或 API 调用的错误)

    # --- 初始化过程的中间状态 ---
    raw_schema_result: Optional[List[str]] = None # 来自 /get_schema API 的原始结果 (Dify 节点 '1742268541036' 的输出)
    raw_table_names_str: Optional[str] = None   # 来自 LLM 的原始表名字符串 (Dify 节点 '1742697648839' 的输出)

    # --- 查询/分析 过程的中间状态 ---
    sql_query_generated: Optional[str] = None   # LLM 生成的 SQL 查询 (Dify 节点 '1742268678777' 或类似的输出)
    sql_result: Optional[str] = None            # 来自 /execute_query API 的结果 (JSON 字符串) (Dify 节点 '1742268852484' 的输出)

    # --- 路由控制状态 ---
    main_intent: Optional[str] = None           # 主意图分类结果 (例如, "query_analysis", "modify", "reset")
    query_analysis_intent: Optional[str] = None # 查询/分析子意图分类结果 (例如, "query", "analysis")

    # --- 修改流程的中间状态 (新增) ---
    modify_context_sql: Optional[str] = None    # 为获取修改上下文而生成的 SELECT SQL
    modify_context_result: Optional[str] = None # 执行上下文 SQL 后返回的 JSON 结果字符串
    raw_modify_llm_output: Optional[str] = None # 修改流程中，LLM解析用户意图后返回的原始 JSON 字符串
    modify_error_message: Optional[str] = None # 修改流程专属错误

    # === 新增流程状态 ===
    temp_add_llm_data: Optional[str] = None # LLM 生成的原始新增内容 JSON 字符串 (可能含占位符) - 重命名自 add_raw_llm_output
    add_structured_records_str: Optional[str] = None # 新增：结构化记录的 JSON 字符串表示
    structured_add_records: Optional[List[Dict[str, Any]]] = None # 初步清理和结构化后的记录列表 (保留，但传递用 str)
    add_processed_records_str: Optional[str] = None # 新增：处理占位符后的记录 JSON 字符串表示
    add_processed_records: Optional[List[Dict[str, Any]]] = None # 新增：处理占位符后的记录 (保留，但传递用 str)
    add_preview_text: Optional[str] = None      # 新增：由 LLM 生成的新增操作预览文本 (给用户看)
    add_error_message: Optional[str] = None # 新增流程专属错误信息

    # === 删除流程状态 ===
    delete_context_sql: Optional[str] = None
    # delete_show: 存储 LLM 格式化的待删除记录预览文本 (给用户看)
    # delete_array: 存储解析后的待删除记录 ID 列表 (给 API)

    # === 新增：复合操作状态 ===
    combined_operation_plan: Optional[List[Dict[str, Any]]] = None # LLM 解析出的统一操作列表
    content_combined: Optional[str] = None # 复合操作的统一预览文本

    # === 保存/确认流程状态 ===
    # save_content: 标记当前暂存的操作类型 ("修改路径", "新增路径", "删除路径", "复合路径")
    # (复用) lastest_content_production: 存储待执行的修改/新增/复合操作负载
    # (复用) delete_array: 存储待执行的删除操作负载
    # (复用) api_call_result: 存储 API 调用结果 (成功或失败消息)

    # === 通用状态 ===
    # ... existing code ... 

    # --- Delete Flow Specific ---
    delete_preview_sql: NotRequired[Optional[str]]  # SQL query to fetch records for delete preview
    delete_show: NotRequired[Optional[str]]         # JSON string result of the preview query
    delete_preview_text: NotRequired[Optional[str]] # User-friendly text preview of records to be deleted
    delete_error_message: NotRequired[Optional[str]] # Specific error messages for delete flow
    content_delete: NotRequired[Optional[str]]      # Staged delete preview text for confirmation flow
    delete_ids_llm_output: NotRequired[Optional[str]] # Raw LLM output when parsing IDs to delete
    delete_ids_structured_str: NotRequired[Optional[str]] # JSON string like '{"table1": ["id1"], "table2": ["id2", "id3"]}'
    delete_api_result: NotRequired[Optional[Any]] # Result from the delete API call(s)

    # --- General ---
    final_answer: NotRequired[str]
    # ... any other existing fields like error_flag ...
    error_flag: NotRequired[bool] # 确保这个或其他通用字段存在 