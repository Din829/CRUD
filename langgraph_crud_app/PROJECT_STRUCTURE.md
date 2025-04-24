langgraph_crud_app/
├── graph/                  # 核心 LangGraph 图定义
│   ├── __init__.py         # 初始化模块
│   ├── state.py            # 定义 GraphState TypedDict
│   └── graph_builder.py    # 构建 LangGraph 图 (定义节点和边)
│
├── nodes/                  # LangGraph 节点函数
│   ├── __init__.py         # 初始化模块
│   ├── routers.py          # 存放流程路由的逻辑函数及节点
│   ├── preprocessing_actions.py # 存放初始化流程的动作节点
│   ├── query_actions.py      # 存放查询/分析流程的动作节点
│   └── flow_control_actions.py # 存放主流程控制的动作节点
│
├── services/               # 可重用的业务逻辑和与外部系统的交互层
│   ├── __init__.py         # 初始化模块
│   ├── api_client.py       # 封装与 Flask API 交互的客户端逻辑
│   ├── llm_preprocessing_service.py # 封装与 LLM 交互的服务逻辑 (初始化流程)
│   ├── llm_query_service.py      # 封装与 LLM 交互的服务逻辑 (查询/分析流程)
│   └── data_processor.py   # 包含数据清理、转换等通用工具函数
│
├── config/                 # 配置管理
│   ├── __init__.py
│   └── settings.py         # API Keys, LLM 配置等
│
├── main.py                 # 应用主入口
├── requirements.txt        # 项目依赖
├── README.md               # 项目说明
├── PROJECT_STRUCTURE.md    # 项目结构说明 (本文档)
├── 前置流程说明.txt        # 初始化流程的详细说明
├── 查询分析流程说明.txt    # 查询/分析流程的详细说明
└── 主要流程控制说明.txt    # 主意图分类和路由说明 