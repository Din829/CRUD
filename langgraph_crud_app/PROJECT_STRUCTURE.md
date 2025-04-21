langgraph_crud_app/
├── graph/                  # 核心 LangGraph 图定义
│   ├── __init__.py         # 初始化模块，可导出编译后的图
│   ├── state.py            # 定义 GraphState TypedDict (包含所有工作流状态)
│   └── graph_builder.py    # 构建 LangGraph 图 (定义节点和边，节点调用 services)
│
├── nodes/                  # LangGraph 节点函数 (负责流程编排和调用 services)
│   ├── __init__.py         # 初始化模块
│   ├── routers.py          # 存放流程路由的逻辑函数及执行路由动作的节点
│   └── actions.py          # 存放执行具体动作 (调用 services) 的节点函数
│
├── services/               # 可重用的业务逻辑和与外部系统的交互层
│   ├── __init__.py         # 初始化模块
│   ├── api_client.py       # 封装与 Flask API 交互的客户端逻辑
│   ├── llm_service.py      # 封装与 LLM 交互的服务逻辑 (分类, 生成 SQL/JSON, 格式化)
│   ├── data_processor.py   # 包含数据清理、转换、状态更新等通用工具函数/类
│   └── placeholder_processor.py # (可选) 封装处理新增操作中占位符逻辑的专用模块
│
├── config/                 # 配置管理 (保持不变)
│   ├── __init__.py
│   └── settings.py         # 数据库连接信息, API Keys 等
│
├── main.py                 # 应用主入口
├── requirements.txt        # 项目依赖 (包含 LangGraph 检查点库)
└── README.md               # 项目说明 (保持不变) 