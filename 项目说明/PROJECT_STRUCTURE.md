langgraph_crud_app/
├── graph/                  # 核心 LangGraph 图定义
│   ├── __init__.py
│   ├── state.py            # 定义 GraphState TypedDict (应用状态结构)
│   │   └── class GraphState(TypedDict): # 包含所有可能的字段 (增加 combined_operation_plan, content_combined, delete_preview_sql等)
│   └── graph_builder.py    # 构建 LangGraph 图
│       ├── _route_after_validation(...)      # 内部路由: 验证修改后
│       ├── _route_after_context_sql_generation(...) # 内部路由: 上下文SQL生成后
│       ├── _route_after_context_sql_execution(...) # 内部路由: 上下文SQL执行后
│       ├── _route_add_flow_on_error(...)     # 内部路由: 新增流程错误检查
│       ├── _route_delete_flow_on_error(...)  # 新增: 内部路由: 删除流程错误检查
│       └── build_graph()                   # 主函数: 创建并配置图 (增加复合和删除流程节点和边)
│
├── nodes/                  # LangGraph 节点 (动作和路由)
│   ├── __init__.py
│   ├── actions/            # 存放动作节点 (执行具体任务)
│   │   ├── __init__.py     # 导出所有动作函数 (包括 composite_actions)
│   │   ├── preprocessing_actions.py # 初始化流程动作
│   │   │   ├── fetch_schema_action(...)        # 调用 API 获取 Schema
│   │   │   ├── extract_table_names_action(...) # LLM 提取表名
│   │   │   ├── process_table_names_action(...) # 字符串转列表并清理表名
│   │   │   ├── format_schema_action(...)       # LLM 格式化 Schema
│   │   │   └── fetch_sample_data_action(...)   # 调用 API 获取数据示例
│   │   ├── query_actions.py      # 查询/分析流程动作
│   │   │   ├── generate_select_sql_action(...) # LLM 生成 SELECT SQL
│   │   │   ├── generate_analysis_sql_action(...)# LLM 生成分析 SQL
│   │   │   ├── clean_sql_action(...)           # 清理 SQL 语句
│   │   │   ├── execute_sql_query_action(...)   # 调用 API 执行 SQL 查询
│   │   │   ├── handle_query_not_found_action(...)# 处理查询无结果
│   │   │   ├── handle_analysis_no_data_action(...)# 处理分析无数据
│   │   │   ├── handle_clarify_query_action(...) # 处理查询需澄清
│   │   │   ├── handle_clarify_analysis_action(...)# 处理分析需澄清
│   │   │   ├── format_query_result_action(...) # LLM 格式化查询结果
│   │   │   └── analyze_analysis_result_action(...)# LLM 分析分析结果
│   │   ├── modify_actions.py     # 修改流程特有动作
│   │   │   ├── generate_modify_context_sql_action(...)# LLM 生成修改上下文 SQL (含 ID 修改检查)
│   │   │   ├── execute_modify_context_sql_action(...) # 执行修改上下文 SQL
│   │   │   ├── parse_modify_request_action(...)     # LLM 解析修改请求 (含上下文)
│   │   │   ├── validate_and_store_modification_action(...) # 验证并存储修改 (JSON 格式)
│   │   │   ├── handle_modify_error_action(...)      # 处理修改流程错误
│   │   │   └── provide_modify_feedback_action(...)  # 提供修改反馈给用户
│   │   ├── add_actions.py        # 新增流程特有动作
│   │   │   ├── parse_add_request_action(...)     # LLM 解析新增请求 (含占位符)
│   │   │   ├── process_add_llm_output_action(...) # 清理和结构化 LLM 输出
│   │   │   ├── process_placeholders_action(...)  # 处理占位符 (查询/随机)
│   │   │   ├── format_add_preview_action(...)    # LLM 格式化新增预览
│   │   │   ├── provide_add_feedback_action(...)  # 提供新增预览反馈给用户
│   │   │   ├── handle_add_error_action(...)      # 处理新增流程错误 (通用)
│   │   │   └── finalize_add_response(...)    # 新增：确保反馈被合并的空节点
│   │   ├── delete_actions.py     # 新增: 删除流程特有动作
│   │   │   ├── generate_delete_preview_sql_action(...) # LLM 生成删除预览 SQL
│   │   │   ├── clean_delete_sql_action(...)     # 清理删除预览 SQL
│   │   │   ├── execute_delete_preview_sql_action(...) # 执行预览SQL获取待删除记录
│   │   │   ├── format_delete_preview_action(...) # LLM 格式化删除预览
│   │   │   ├── provide_delete_feedback_action(...) # 提供删除预览反馈给用户
│   │   │   ├── handle_delete_error_action(...)  # 处理删除流程错误
│   │   │   └── finalize_delete_response(...)   # 确保删除反馈被合并的空节点
│   │   ├── composite_actions.py # 新增: 复合操作动作
│   │   │   ├── parse_combined_request_action(...) # LLM 解析复合请求为操作列表
│   │   │   ├── process_composite_placeholders_action(...) # 新增: 处理 db/random 占位符
│   │   │   └── format_combined_preview_action(...)  # LLM 格式化复合操作预览
│   │   └── flow_control_actions.py # 主流程控制及确认流程动作 (更新以处理复合和删除路径)
│   │       ├── handle_reset_action(...)          # 处理重置意图
│   │       ├── handle_modify_intent_action(...)  # (占位符)
│   │       ├── handle_add_intent_action(...)     # (占位符)
│   │       ├── handle_delete_intent_action(...)  # (占位符)
│   │       ├── handle_confirm_other_action(...)  # (占位符)
│   │       ├── stage_modify_action(...)          # 暂存修改操作并请求确认
│   │       ├── stage_add_action(...)             # 暂存新增操作并请求确认
│   │       ├── stage_combined_action(...)        # 新增: 暂存复合操作并请求确认
│   │       ├── stage_delete_action(...)          # 新增: 暂存删除操作并请求确认
│   │       ├── handle_nothing_to_stage_action(...) # 处理无法暂存的情况
│   │       ├── handle_invalid_save_state_action(...) # 处理无效保存状态
│   │       ├── cancel_save_action(...)           # 用户取消保存
│   │       ├── execute_operation_action(...)     # 执行暂存的操作 (修改/新增/复合/删除)
│   │       ├── reset_after_operation_action(...) # 操作后清空相关状态 (包括复合和删除)
│   │       └── format_operation_response_action(...)# LLM 格式化操作结果 (包括复合和删除)
│   │
│   └── routers/            # 存放路由节点 (决策流程走向)
│       ├── __init__.py     # 导出所有路由节点和逻辑
│       ├── initialization_router.py # 初始化路由
│       │   ├── _get_initialization_route(...)    # 路由逻辑: 判断是否初始化
│       │   └── route_initialization_node(...)    # 图入口节点，检查状态并重置错误
│       ├── main_router.py          # 主意图路由
│       │   ├── classify_main_intent_node(...)  # 路由节点: LLM 分类主意图
│       │   └── _route_after_main_intent(...)   # 路由逻辑: 根据主意图分发 (增加 composite/delete)
│       ├── query_analysis_router.py # 查询/分析子意图及结果路由
│       │   ├── classify_query_analysis_node(...) # 路由节点: LLM 子意图分类 (查询/分析)
│       │   ├── _route_query_or_analysis(...)     # 路由逻辑: 分发到查询或分析分支
│       │   ├── route_after_query_execution_node(...) # 路由节点: SQL 执行后连接点
│       │   └── _route_after_query_execution(...) # 路由逻辑: 根据 SQL 结果路由
│       ├── delete_flow_router.py   # 新增: 删除流程路由
│       │   ├── route_delete_flow_node(...)    # 路由节点: 删除流程入口 (空)
│       │   └── _route_delete_flow_logic(...)  # 路由逻辑: 删除流程状态转移
│       └── confirmation_router.py  # 确认流程路由 (更新以处理复合和删除路径)
│           ├── route_confirmation_entry(...)     # 路由节点: 确认流程入口 (空)
│           ├── stage_operation_node(...)       # 路由节点: 尝试暂存操作入口 (空)
│           ├── check_staged_operation_node(...)# 路由节点: 检查已暂存操作入口 (空)
│           ├── ask_confirm_modify_node(...)    # 路由节点: 询问是否确认修改/新增/复合/删除入口 (空)
│           ├── _route_confirmation_entry_logic(...) # 路由逻辑: 确认入口决策
│           ├── _stage_operation_logic(...)       # 路由逻辑: 判断暂存类型 (增加 delete)
│           ├── _check_staged_operation_logic(...) # 路由逻辑: 检查暂存状态 (增加 delete_show)
│           └── _ask_confirm_modify_logic(...)    # 路由逻辑: LLM 判断用户是否确认 (通用)
│
├── services/               # 可重用的业务逻辑和与外部系统的交互层
│   ├── __init__.py
│   ├── api_client.py       # 封装与后端 API (Flask) 交互的客户端逻辑
│   │   ├── get_schema()                  # 获取数据库 Schema
│   │   ├── execute_query(...)            # 执行 SELECT SQL 查询
│   │   ├── update_record(...)            # 更新记录
│   │   ├── insert_record(...)            # 插入新记录
│   │   ├── delete_record(...)            # 删除记录
│   │   └── execute_batch_operations(...) # 新增: 执行批量操作
│   ├── data_processor.py   # 包含数据清理、转换、占位符处理等通用工具函数
│   │   ├── nl_string_to_list(...)        # 换行符分隔字符串转列表
│   │   ├── clean_sql_string(...)         # 清理 SQL 字符串
│   │   ├── is_query_result_empty(...)    # 检查查询结果是否为空
│   │   ├── clean_and_structure_llm_add_output(...) # 清理/结构化新增LLM输出
│   │   ├── extract_placeholders(...)     # 从结构化记录提取占位符
│   │   └── process_placeholders(...)     # 处理 {{...}} 占位符 (db/random, 忽略 new)
│   └── llm/                # LLM 相关服务封装
│       ├── __init__.py
│       ├── llm_preprocessing_service.py # 初始化流程 LLM 服务
│       │   ├── extract_table_names(...)      # LLM 提取表名
│       │   └── format_schema(...)            # LLM 格式化 Schema
│       ├── llm_query_service.py      # 查询/分析流程 LLM 服务
│       │   ├── classify_main_intent(...)     # LLM 分类主意图
│       │   ├── classify_query_analysis_intent(...)# LLM 查询/分析子意图分类
│       │   ├── generate_select_sql(...)      # LLM 生成 SELECT SQL
│       │   ├── generate_analysis_sql(...)    # LLM 生成分析 SQL
│       │   ├── format_query_result(...)      # LLM 格式化查询结果
│       │   └── analyze_analysis_result(...)  # LLM 分析分析结果
│       ├── llm_modify_service.py     # 修改流程 LLM 服务
│       │   ├── _escape_json_for_prompt(...)  # (内部) 转义 JSON 中的花括号
│       │   ├── parse_modify_request(...)     # LLM 解析修改请求 (含上下文)
│       │   ├── generate_modify_context_sql(...) # LLM 生成修改上下文 SQL
│       │   └── check_for_direct_id_modification_intent(...) # LLM 检查直接修改 ID 意图
│       ├── llm_add_service.py        # 新增流程 LLM 服务
│       │   ├── parse_add_request(...)        # LLM 解析新增请求 (含占位符)
│       │   └── format_add_preview(...)       # LLM 格式化新增预览
│       ├── llm_delete_service.py     # 新增: 删除流程 LLM 服务
│       │   ├── _escape_json_for_prompt(...)  # (内部) 转义 JSON 中的花括号
│       │   ├── generate_delete_preview_sql(...) # LLM 生成删除预览 SQL
│       │   ├── format_delete_preview(...)    # LLM 格式化删除预览
│       │   ├── parse_delete_ids(...)         # LLM 解析待删除记录的 ID (不稳定)
│       │   └── parse_delete_ids_direct(...)  # 直接解析待删除记录的 ID (稳定实现)
│       ├── llm_composite_service.py # 新增: 复合操作 LLM 服务
│       │   ├── parse_combined_request(...)     # LLM 解析复合请求为操作列表
│       │   └── format_combined_preview(...)    # LLM 格式化复合操作预览
│       ├── llm_error_service.py     # 新增: 错误处理 LLM 服务
│       │   ├── translate_flask_error(...)      # LLM 转换Flask技术错误为用户友好信息
│       │   ├── _analyze_error_type(...)        # (内部) 分析错误类型
│       │   ├── _fallback_error_translation(...) # (内部) 基于规则的错误转换回退
│       │   ├── format_database_constraint_error(...) # 专门处理数据库约束错误
│       │   └── _get_friendly_field_name(...)   # (内部) 转换字段名为用户友好名称
│       └── llm_flow_control_service.py # 主流程/确认流程 LLM 服务
│           ├── classify_yes_no(...)          # LLM 判断用户是否确认 (是/否)
│           └── format_api_result(...)      # LLM 格式化 API 操作结果 (支持删除结果)
│
├── config/                 # 配置管理
│   ├── __init__.py
│   └── settings.py         # API Keys, LLM 配置等 (通过 pydantic-settings 加载 .env)
│
├── app.py                  # Flask 后端 API (包含 /delete_record 和 /execute_batch_operations)
├── main.py                 # 应用主入口
│   └── main()              # 加载配置, 构建图, 运行交互循环
├── requirements.txt        # Python 依赖库
├── README.md               # 项目说明
├── PROJECT_STRUCTURE.md    # 项目结构说明 (本文档)
├── 复合流程说明.txt        # 复合流程实现进度
├── 删除流程说明.txt        # 新增: 删除流程实现进度
└── .cursor/                # Cursor IDE 配置 (可选)

# --- CI/CD (持续集成/持续部署) ---
# .github/
# └── workflows/            # 存放 CI/CD 工作流程配置文件 (例如 GitHub Actions 的 .yml 文件)

# --- 外部文件 (辅助理解 Dify 逻辑) ---
# ... (省略 Dify 相关文件列表)
