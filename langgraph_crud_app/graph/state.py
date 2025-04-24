# state.py: 定义 LangGraph 应用的状态 TypedDict。

from typing import List, TypedDict, Optional, Any

class GraphState(TypedDict):
    """
    表示 LangGraph 应用的状态，映射 Dify 的 conversation 变量并包含必要的工作流字段。
    """
    # --- 核心 Dify conversation 变量 (镜像) ---
    biaojiegou_save: Optional[str]       # 格式化后的 Schema JSON 字符串 (来自 Dify 节点 '1742268574820')
    table_names: Optional[List[str]]     # 从 Schema 中提取的表名列表 (来自 Dify 节点 '1743382507830')
    data_sample: Optional[str]           # 数据示例 JSON 字符串 (来自 Dify 节点 '1742695585674')
    content_modify: Optional[str]        # 面向用户的修改操作预览内容 (由 LLM 生成，保存以供确认)
    content_new: Optional[str]           # 面向用户的创建操作预览内容 (由 LLM 生成，保存以供确认)
    delete_show: Optional[str]           # 面向用户的删除操作预览内容 (查询结果，保存以供确认)
    lastest_content_production: Optional[List[str]] # 创建/更新 API 调用的原始结构化负载 (JSON 字符串列表) (确认前准备)
    delete_array: Optional[List[str]]    # 删除 API 调用的原始结构化负载 (JSON 字符串列表) (确认前准备)
    save_content: Optional[str]          # 控制标志，指示待处理的保存操作: "修改路径", "新增路径", "删除路径", 或 None (请求用户确认前设置)
    # id_check: Optional[str]            # Dify 变量，用途不明确，暂时省略，除非需要

    # --- 工作流输入 / 输出 ---
    query: str                           # 用户的输入查询 (来自 Dify 'sys.query')
    final_answer: Optional[str]          # 给用户的最终回复 (由 Dify 中的 Answer 节点生成)
    error_message: Optional[str]         # 存储执行期间的错误信息 (捕获来自 Code 节点或 API 调用的错误)

    # --- 初始化过程的中间状态 ---
    raw_schema_result: Optional[List[str]] # 来自 /get_schema API 的原始结果 (Dify 节点 '1742268541036' 的输出)
    raw_table_names_str: Optional[str]   # 来自 LLM 的原始表名字符串 (Dify 节点 '1742697648839' 的输出)

    # --- 查询/分析 过程的中间状态 ---
    sql_query_generated: Optional[str]   # LLM 生成的 SQL 查询 (Dify 节点 '1742268678777' 或类似的输出)
    sql_result: Optional[str]            # 来自 /execute_query API 的结果 (JSON 字符串) (Dify 节点 '1742268852484' 的输出)

    # --- 路由控制状态 ---
    main_intent: Optional[str]           # 主意图分类结果 (e.g., "query_analysis", "modify", "reset")
    query_analysis_intent: Optional[str] # 查询/分析子意图分类结果 (e.g., "query", "analysis")

    # --- API 调用前 LLM 生成的中间状态 ---
    # (目前使用 lastest_content_production 和 delete_array, 镜像 Dify 的变量用法)
    # llm_generated_update_payload: Optional[List[Dict]] # 如果解析 JSON 字符串，可以使用此字段
    # llm_generated_insert_payload: Optional[List[Dict]] # 如果解析 JSON 字符串，可以使用此字段
    # llm_generated_delete_payload: Optional[List[Dict]] # 如果解析 JSON 字符串，可以使用此字段 