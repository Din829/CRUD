langgraph_crud_app/
├── graph/                  # 核心 LangGraph 图定义
│   ├── __init__.py         # 初始化模块
│   ├── state.py            # 定义 GraphState TypedDict
│   └── graph_builder.py    # 构建 LangGraph 图 (定义节点和边, 包括内部路由函数)
│
├── nodes/                  # LangGraph 节点函数
│   ├── __init__.py         # 初始化模块
│   ├── actions/            # 存放动作节点
│   │   ├── __init__.py
│   │   ├── preprocessing_actions.py # 初始化流程动作
│   │   │   ├── fetch_schema_action          # 调用 API 获取 Schema
│   │   │   ├── extract_table_names_action   # LLM 提取表名
│   │   │   ├── process_table_names_action   # 字符串转列表并清理表名
│   │   │   ├── format_schema_action         # LLM 格式化 Schema
│   │   │   └── fetch_sample_data_action     # 调用 API 获取数据示例
│   │   ├── query_actions.py      # 查询/分析流程动作
│   │   │   ├── generate_select_sql_action   # LLM 生成 SELECT SQL
│   │   │   ├── generate_analysis_sql_action # LLM 生成分析 SQL
│   │   │   ├── clean_sql_action             # 清理 SQL 语句
│   │   │   ├── execute_sql_query_action     # 调用 API 执行 SQL 查询
│   │   │   ├── handle_query_not_found_action # 处理查询无结果
│   │   │   ├── handle_analysis_no_data_action# 处理分析无数据
│   │   │   ├── handle_clarify_query_action  # 处理查询需澄清
│   │   │   ├── handle_clarify_analysis_action# 处理分析需澄清
│   │   │   ├── format_query_result_action   # LLM 格式化查询结果
│   │   │   └── analyze_analysis_result_action# LLM 分析分析结果
│   │   ├── flow_control_actions.py # 主流程控制及确认流程动作
│   │   │   ├── handle_reset_action          # 处理重置意图
│   │   │   ├── handle_modify_intent_action  # 处理修改意图 (占位符)
│   │   │   ├── handle_add_intent_action     # 处理新增意图 (占位符)
│   │   │   ├── handle_delete_intent_action  # 处理删除意图 (占位符)
│   │   │   ├── handle_confirm_other_action# 处理确认/其他意图 (占位符)
│   │   │   ├── stage_modify_action          # 暂存修改操作并请求确认
│   │   │   ├── handle_nothing_to_stage_action # 处理无法暂存的情况
│   │   │   ├── handle_invalid_save_state_action # 处理无效保存状态
│   │   │   ├── cancel_save_action           # 用户取消保存
│   │   │   ├── execute_modify_action        # 执行修改 (转换数据并调用 API)
│   │   │   ├── reset_after_modify_action    # 修改后清空状态
│   │   │   └── format_modify_response_action# LLM 格式化修改结果
│   │   └── modify_actions.py     # 修改流程特有动作
│   │       ├── generate_modify_context_sql_action  # 调用 LLM 意图检查；若通过，则生成修改上下文查询 SQL
│   │       ├── execute_modify_context_sql_action   # 执行修改上下文查询 SQL
│   │       ├── parse_modify_request_action         # LLM 解析修改请求 (利用上下文)
│   │       ├── validate_and_store_modification_action # 验证并存储修改内容
│   │       ├── handle_modify_error_action          # 处理修改流程错误
│   │       └── provide_modify_feedback_action      # 提供修改反馈给用户
│   └── routers/            # 存放路由节点和逻辑
│       ├── __init__.py
│       ├── initialization_router.py # 初始化路由
│       │   ├── route_initialization_node    # 图入口节点，检查状态并重置错误
│       │   └── _get_initialization_route    # 路由逻辑: 判断是否初始化
│       ├── main_router.py          # 主意图路由
│       │   ├── classify_main_intent_node  # 路由节点: LLM 分类主意图
│       │   └── _route_after_main_intent   # 路由逻辑: 根据主意图分发
│       ├── query_analysis_router.py # 查询/分析路由
│       │   ├── classify_query_analysis_node # 路由节点: LLM 子意图分类 (查询/分析)
│       │   ├── _route_query_or_analysis     # 路由逻辑: 分发到查询或分析分支
│       │   ├── route_after_query_execution_node # 路由节点: SQL 执行后连接点
│       │   └── _route_after_query_execution # 路由逻辑: 根据 SQL 结果路由
│       └── confirmation_router.py  # 确认流程路由
│           ├── route_confirmation_entry     # 路由节点: 确认流程入口
│           ├── stage_operation_node       # 路由节点: 尝试暂存操作入口
│           ├── check_staged_operation_node# 路由节点: 检查已暂存操作入口
│           ├── ask_confirm_modify_node    # 路由节点: 询问是否确认修改入口
│           ├── _route_confirmation_entry_logic # 路由逻辑: 确认入口决策
│           ├── _stage_operation_logic       # 路由逻辑: 判断暂存类型
│           ├── _check_staged_operation_logic # 路由逻辑: 检查暂存状态
│           └── _ask_confirm_modify_logic    # 路由逻辑: LLM 判断用户是否确认
│
├── services/               # 可重用的业务逻辑和与外部系统的交互层
│   ├── __init__.py         # 初始化模块
│   ├── api_client.py       # 封装与 Flask API 交互的客户端逻辑
│   ├── data_processor.py   # 包含数据清理、转换等通用工具函数
│   ├── placeholder_processor.py # (用途待确认)
│   └── llm/                # LLM 相关服务
│       ├── __init__.py
│       ├── llm_preprocessing_service.py # 封装与 LLM 交互的服务逻辑 (初始化流程)
│       │   ├── extract_table_names      # 使用 LLM 从用户查询和 Schema 中提取目标表名
│       │   └── format_schema_for_llm    # 使用 LLM 清理和格式化数据库 Schema
│       ├── llm_query_service.py      # 封装与 LLM 交互的服务逻辑 (查询/分析流程)
│       │   ├── generate_select_sql      # 使用 LLM 根据用户查询生成 SELECT SQL 语句
│       │   ├── generate_analysis_sql    # 使用 LLM 根据用户查询生成用于数据分析的 SQL 语句
│       │   ├── format_query_result      # 使用 LLM 格式化 SQL 查询结果
│       │   └── analyze_analysis_result  # 使用 LLM 分析数据分析 SQL 的结果
│       ├── llm_flow_control_service.py # 封装与 LLM 交互的服务逻辑 (主流程控制)
│       │   ├── classify_main_intent     # 使用 LLM 分类用户在主流程中的意图
│       │   ├── classify_query_analysis_intent # 使用 LLM 在查询/分析流程中对用户意图进行二次分类
│       │   ├── ask_confirm_modify       # 使用 LLM 判断用户是否确认待执行的修改操作
│       │   ├── format_modify_response   # 使用 LLM 格式化修改操作的最终结果反馈给用户
│       │   └── format_general_response  # 使用 LLM 生成通用回复 (例如，澄清、错误处理)
│       └── llm_modify_service.py     # 修改流程 LLM 服务
│           ├── check_for_direct_id_modification_intent # LLM 判断用户是否明确要求修改主键 ID
│           ├── parse_modify_request     # LLM 解析修改请求 (利用上下文)
│           └── generate_modify_context_sql # LLM 生成修改上下文查询 SQL
│
├── config/                 # 配置管理
│   ├── __init__.py
│   └── settings.py         # API Keys, LLM 配置等
│
├── main.py                 # 应用主入口
├── requirements.txt        # 项目依赖
├── README.md               # 项目说明
├── PROJECT_STRUCTURE.md    # 项目结构说明 (本文档)
└── .cursor/                # Cursor IDE 配置 (可选)

├── 前置流程说明.txt        # 初始化流程的详细说明
├── 查询分析流程说明.txt    # 查询/分析流程的详细说明
└── 主要流程控制说明.txt    # 主意图分类和路由说明 