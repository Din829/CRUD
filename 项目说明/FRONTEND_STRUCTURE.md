frontend/
├── src/                    # 前端源代码目录
│   ├── app/                # Next.js 14 App Router 目录 (页面和布局)
│   │   ├── layout.tsx      # 根布局组件 (全局 HTML 结构, 字体配置, 元数据)
│   │   │   ├── RootLayout({children})       # React 根布局组件
│   │   │   ├── metadata: Metadata          # SEO 元数据配置
│   │   │   └── Inter 字体集成              # Google Fonts 字体配置
│   │   ├── page.tsx        # 首页组件 (主聊天界面布局)
│   │   │   ├── Home()                      # 主页组件
│   │   │   ├── 聊天区域布局                 # 左侧对话界面
│   │   │   ├── 数据展示区域布局              # 右侧数据面板
│   │   │   ├── 输入框和发送按钮              # 用户交互控件
│   │   │   └── 响应式网格布局                # Tailwind 响应式设计
│   │   ├── globals.css     # 全局样式文件 (Tailwind + CSS 变量)
│   │   │   ├── @tailwind base/components/utilities # Tailwind 指令
│   │   │   ├── CSS 变量定义 (:root)         # 颜色主题变量
│   │   │   ├── 深色模式支持 (.dark)         # 暗黑主题变量
│   │   │   └── 基础样式重置                 # 全局样式重置
│   │   ├── chat/           # 🚧 未来: 聊天功能页面
│   │   │   └── page.tsx    # 专门的聊天页面 (如果需要独立路由)
│   │   ├── data/           # 🚧 未来: 数据管理页面  
│   │   │   └── page.tsx    # 数据浏览和管理页面
│   │   └── api/            # 🚧 未来: API 路由 (如果需要服务端 API)
│       │   └── backend/    # 代理路由 (已在 next.config.js 配置)
│
│   ├── components/         # React 组件库 (UI 组件和业务组件)
│   │   ├── ui/             # 基础 UI 组件 (Shadcn/ui 组件库)
│   │   │   ├── button.tsx           # ✅ 按钮组件 (多种变体和尺寸)
│   │   │   ├── input.tsx            # ✅ 输入框组件 (表单输入控件)
│   │   │   ├── card.tsx             # ✅ 卡片组件 (容器组件)
│   │   │   ├── table.tsx            # ✅ 表格组件 (数据展示) - Shadcn/ui
│   │   │   ├── dialog.tsx           # 🚧 对话框组件 (模态窗口)
│   │   │   ├── badge.tsx            # 🚧 徽章组件 (状态标识)
│   │   │   ├── avatar.tsx           # 🚧 头像组件 (用户头像)
│   │   │   ├── dropdown-menu.tsx    # 🚧 下拉菜单组件
│   │   │   ├── toast.tsx            # 🚧 提示消息组件
│   │   │   ├── loading.tsx          # 🚧 加载指示器组件
│   │   │   └── ...                  # 🚧 其他 Shadcn/ui 组件
│   │   │
│   │   ├── chat/           # 聊天相关业务组件
│   │   │   ├── ChatInterface.tsx    # 聊天主界面容器 (整合所有聊天组件)
│   │   │   ├── MessageList.tsx      # 消息列表组件 (显示对话历史)
│   │   │   │   ├── renderMessages()        # 渲染消息列表逻辑
│   │   │   │   ├── scrollToBottom()        # 自动滚动到底部
│   │   │   │   └── 虚拟滚动优化             # 长列表性能优化
│   │   │   ├── MessageBubble.tsx    # 消息气泡组件 (单条消息显示)
│   │   │   │   ├── UserMessage              # 用户消息样式
│   │   │   │   ├── AssistantMessage         # AI 助手消息样式
│   │   │   │   ├── 时间戳显示               # 消息时间格式化
│   │   │   │   ├── 消息状态指示器           # 发送/接收状态
│   │   │   │   └── Markdown 渲染支持        # 富文本消息支持
│   │   │   ├── InputArea.tsx        # 输入区域组件 (消息输入和发送)
│   │   │   │   ├── TextInput                # 文本输入框
│   │   │   │   ├── SendButton               # 发送按钮
│   │   │   │   ├── 快捷键支持 (Enter/Shift+Enter) # 键盘交互
│   │   │   │   ├── 输入验证                 # 输入内容验证
│   │   │   │   └── 字符计数器               # 输入长度限制
│   │   │   ├── TypingIndicator.tsx  # 打字指示器 (AI 思考状态)
│   │   │   │   ├── 动画效果                 # CSS 动画实现
│   │   │   │   ├── 状态管理                 # 显示/隐藏控制
│   │   │   │   └── 可配置文本               # 自定义提示文本
│   │   │   ├── QuickActions.tsx     # 快捷操作按钮 (常用命令快捷方式)
│   │   │   │   ├── 预设查询按钮             # 常见查询模板
│   │   │   │   ├── 清空对话                 # 重置对话状态
│   │   │   │   ├── 导出对话                 # 导出聊天记录
│   │   │   │   └── 帮助信息                 # 使用指南
│   │   │   └── ChatHistory.tsx      # 🚧 未来: 对话历史管理
│   │   │       ├── 会话列表                 # 历史对话列表
│   │   │       ├── 会话搜索                 # 对话内容搜索
│   │   │       └── 会话管理                 # 删除/重命名会话
│   │   │
│   │   ├── data/           # 数据展示相关组件
│   │   │   ├── TableDisplay.tsx     # ✅ 数据表格展示 (查询结果显示)
│   │   │   │   ├── ✅ TanStack Table 集成   # React Table v8 强大表格
│   │   │   │   ├── ✅ 动态列生成             # 根据数据自动生成列定义
│   │   │   │   ├── ✅ 排序功能               # 点击列头排序 (升序/降序)
│   │   │   │   ├── ✅ 全局搜索               # 跨列数据搜索筛选
│   │   │   │   ├── ✅ 分页控件               # 数据分页显示 (10条/页)
│   │   │   │   ├── ✅ 数据类型格式化         # 数字、布尔值、长文本智能显示
│   │   │   │   ├── ✅ 加载/错误/空状态      # 完整的状态处理
│   │   │   │   └── 🚧 导出功能               # CSV/Excel 导出 (待开发)
│   │   │   ├── SchemaView.tsx       # ✅ 数据库结构展示 (表结构可视化)
│   │   │   │   ├── ✅ TableList             # 数据库表列表，可折叠展开
│   │   │   │   ├── ✅ ColumnDetails         # 列详情显示，类型颜色标识
│   │   │   │   ├── ✅ 实时统计信息           # 表记录数统计
│   │   │   │   ├── ✅ 搜索表/列             # 结构搜索功能
│   │   │   │   └── ✅ 折叠/展开树形结构     # 层级结构导航
│   │   │   ├── PreviewCard.tsx      # 操作预览卡片 (修改/新增预览)
│   │   │   │   ├── ChangePreview            # 变更内容预览
│   │   │   │   ├── DiffDisplay              # 差异对比显示
│   │   │   │   ├── ConfirmActions           # 确认/取消按钮
│   │   │   │   └── ImpactAnalysis           # 影响范围分析
│   │   │   ├── ResultFormatter.tsx  # 结果格式化器 (智能结果展示)
│   │   │   │   ├── JSONFormatter            # JSON 数据格式化
│   │   │   │   ├── SQLFormatter             # SQL 语句格式化
│   │   │   │   ├── NumberFormatter          # 数值格式化
│   │   │   │   ├── DateTimeFormatter        # 日期时间格式化
│   │   │   │   └── HTMLRenderer             # HTML 内容渲染
│   │   │   ├── ChartDisplay.tsx     # 🚧 未来: 图表展示组件
│   │   │   │   ├── BarChart                 # 柱状图
│   │   │   │   ├── LineChart                # 折线图
│   │   │   │   ├── PieChart                 # 饼图
│   │   │   │   └── CustomChart              # 自定义图表
│   │   │   └── DataExport.tsx       # 🚧 未来: 数据导出组件
│   │   │       ├── ExportOptions            # 导出选项配置
│   │   │       ├── FormatSelector           # 格式选择器
│   │   │       └── DownloadManager          # 下载管理
│   │   │
│   │   ├── dialogs/        # 对话框和模态窗口组件
│   │   │   ├── ConfirmationDialog.tsx # 确认对话框 (操作确认)
│   │   │   │   ├── ConfirmDialog            # 通用确认对话框
│   │   │   │   ├── DestructiveConfirm       # 危险操作确认
│   │   │   │   ├── BulkActionConfirm        # 批量操作确认
│   │   │   │   └── CustomConfirm            # 自定义确认对话框
│   │   │   ├── ErrorDialog.tsx        # 错误提示框 (错误信息展示)
│   │   │   │   ├── ErrorDisplay             # 错误信息格式化
│   │   │   │   ├── ErrorDetails             # 详细错误信息
│   │   │   │   ├── RetryActions             # 重试操作按钮
│   │   │   │   └── ErrorReporting           # 错误反馈功能
│   │   │   ├── LoadingDialog.tsx      # 加载对话框 (长时间操作)
│   │   │   │   ├── ProgressIndicator        # 进度指示器
│   │   │   │   ├── CancelOption             # 取消操作选项
│   │   │   │   ├── StepIndicator            # 步骤指示器
│   │   │   │   └── TimeEstimate             # 预计完成时间
│   │   │   ├── SettingsDialog.tsx     # 🚧 未来: 设置对话框
│   │   │   │   ├── 主题设置                 # 深色/浅色模式
│   │   │   │   ├── 语言设置                 # 多语言支持
│   │   │   │   ├── 快捷键配置               # 自定义快捷键
│   │   │   │   └── 数据显示选项             # 显示偏好设置
│   │   │   └── HelpDialog.tsx         # 🚧 未来: 帮助对话框
│   │   │       ├── 使用指南                 # 功能使用说明
│   │   │       ├── 示例查询                 # 查询示例展示
│   │   │       ├── 快捷键说明               # 键盘快捷键列表
│   │   │       └── 常见问题                 # FAQ 内容
│   │   │
│   │   └── layout/         # 布局相关组件
│       │   ├── Header.tsx           # 顶部导航栏 (应用标题和导航)
│       │   │   ├── AppLogo                  # 应用 Logo
│       │   │   ├── Navigation               # 主导航菜单
│       │   │   ├── UserMenu                 # 用户菜单 (未来功能)
│       │   │   ├── ThemeToggle              # 主题切换按钮
│       │   │   ├── SettingsButton           # 设置按钮
│       │   │   └── HelpButton               # 帮助按钮
│       │   ├── Sidebar.tsx          # 侧边栏 (功能导航和快捷操作)
│       │   │   ├── FunctionNav              # 功能导航菜单
│       │   │   ├── RecentQueries            # 最近查询历史
│       │   │   ├── SavedQueries             # 收藏的查询
│       │   │   ├── DatabaseInfo             # 数据库信息面板
│       │   │   └── CollapsibleControl       # 折叠/展开控制
│       │   ├── Footer.tsx           # 底部信息栏 (状态信息和链接)
│       │   │   ├── StatusInfo               # 连接状态信息
│       │   │   ├── VersionInfo              # 版本信息
│       │   │   ├── DatabaseStatus           # 数据库连接状态
│       │   │   ├── PerformanceInfo          # 性能信息
│       │   │   └── SupportLinks             # 支持链接
│       │   ├── LoadingScreen.tsx    # 全屏加载界面 (应用初始化)
│       │   │   ├── LogoAnimation            # Logo 动画效果
│       │   │   ├── ProgressBar              # 加载进度条
│       │   │   ├── LoadingText              # 加载状态文本
│       │   │   └── BackgroundPattern        # 背景图案
│       │   └── ErrorBoundary.tsx    # 错误边界组件 (错误捕获和恢复)
│           │   ├── ErrorFallback            # 错误回退 UI
│           │   ├── ErrorReporting           # 自动错误报告
│           │   ├── RecoveryActions          # 恢复操作选项
│           │   └── DeveloperInfo            # 开发者错误信息
│
│   ├── lib/                # 工具库和核心服务
│   │   ├── utils.ts        # 通用工具函数
│   │   │   ├── cn(...inputs)               # Tailwind 类名合并工具
│   │   │   ├── formatDate(date)            # 日期格式化函数
│   │   │   ├── formatNumber(num)           # 数字格式化函数
│   │   │   ├── debounce(fn, delay)         # 防抖函数
│   │   │   ├── throttle(fn, delay)         # 节流函数
│   │   │   ├── generateId()                # 唯一 ID 生成器
│   │   │   ├── validateEmail(email)        # 邮箱验证
│   │   │   ├── copyToClipboard(text)       # 复制到剪贴板
│   │   │   └── downloadFile(data, filename) # 文件下载工具
│   │   ├── api.ts          # ✅ API 客户端 (与后端通信)
│   │   │   ├── ✅ axios 实例配置            # HTTP 客户端配置
│   │   │   ├── ✅ 请求/响应拦截器           # 请求预处理和错误处理
│   │   │   ├── ✅ ApiClient 类             # 静态方法 API 客户端
│   │   │   ├── ✅ sendMessage()            # LangGraph 聊天接口
│   │   │   ├── ✅ getSchema()              # 获取数据库结构
│   │   │   ├── ✅ executeQuery(sql)        # 执行 SQL 查询
│   │   │   ├── ✅ updateRecord(data)       # 更新数据记录
│   │   │   ├── ✅ insertRecord(data)       # 插入新记录
│   │   │   ├── ✅ deleteRecord(data)       # 删除记录
│   │   │   ├── ✅ executeBatchOperations(ops) # 批量操作执行
│   │   │   └── 🚧 未来扩展 API 方法        # 图表、导出等功能
│   │   ├── dataParser.ts   # ✅ 数据解析工具 (从聊天消息提取数据)
│   │   │   ├── ✅ extractTableDataFromMessage() # 提取JSON/表格数据
│   │   │   ├── ✅ parseTextTable()         # 解析文本表格格式
│   │   │   ├── ✅ createQueryResult()      # 创建QueryResult对象
│   │   │   ├── ✅ hasQueryResult()         # 检查消息是否包含查询结果
│   │   │   └── ✅ extractStatistics()      # 提取统计信息
│   │   ├── constants.ts    # 应用常量定义
│   │   │   ├── API_ENDPOINTS              # API 端点常量
│   │   │   ├── UI_CONSTANTS               # UI 相关常量
│   │   │   ├── MESSAGE_TYPES              # 消息类型枚举
│   │   │   ├── QUERY_LIMITS               # 查询限制常量
│   │   │   ├── STORAGE_KEYS               # 本地存储键名
│   │   │   ├── THEME_OPTIONS              # 主题选项常量
│   │   │   └── ERROR_CODES                # 错误代码常量
│   │   ├── validators.ts   # 数据验证函数
│   │   │   ├── validateSQL(sql)           # SQL 语句验证
│   │   │   ├── validateFormData(data)     # 表单数据验证
│   │   │   ├── validateFileUpload(file)   # 文件上传验证
│   │   │   └── sanitizeUserInput(input)   # 用户输入清理
│   │   ├── formatters.ts   # 数据格式化工具
│   │   │   ├── formatTableData(data)      # 表格数据格式化
│   │   │   ├── formatQueryResult(result)  # 查询结果格式化
│   │   │   ├── formatFileSize(bytes)      # 文件大小格式化
│   │   │   ├── formatDuration(ms)         # 时间间隔格式化
│   │   │   └── formatSQLQuery(sql)        # SQL 格式化美化
│   │   └── 🚧 未来扩展库文件               # 根据功能需求添加
│       │   ├── chart-utils.ts            # 图表工具函数
│       │   ├── export-utils.ts           # 导出功能工具
│       │   ├── sql-parser.ts             # SQL 解析工具
│       │   └── websocket.ts              # WebSocket 客户端
│
│   ├── hooks/              # React 自定义 Hooks
│   │   ├── useConversation.ts # 对话状态管理 Hook
│   │   │   ├── useConversationState()     # 对话状态管理
│   │   │   ├── useSendMessage()           # 发送消息逻辑
│   │   │   ├── useMessageHistory()        # 消息历史管理
│   │   │   ├── useClearConversation()     # 清空对话功能
│   │   │   └── useTypingState()           # 打字状态管理
│   │   ├── useAPI.ts        # API 调用管理 Hook
│   │   │   ├── useAPICall()               # 通用 API 调用 Hook
│   │   │   ├── useQuery()                 # 查询操作 Hook
│   │   │   ├── useMutation()              # 修改操作 Hook
│   │   │   ├── useSchema()                # 数据库结构获取
│   │   │   ├── useLoadingState()          # 加载状态管理
│   │   │   └── useErrorHandler()          # 错误处理 Hook
│   │   ├── useTableData.ts  # 表格数据处理 Hook
│   │   │   ├── useTableState()            # 表格状态管理
│   │   │   ├── useSorting()               # 排序功能 Hook
│   │   │   ├── useFiltering()             # 筛选功能 Hook
│   │   │   ├── usePagination()            # 分页功能 Hook
│   │   │   ├── useSelection()             # 行选择功能
│   │   │   └── useTableExport()           # 表格导出功能
│   │   ├── useConfirmation.ts # 确认流程管理 Hook
│   │   │   ├── useConfirmDialog()         # 确认对话框 Hook
│   │   │   ├── useOperationConfirm()      # 操作确认流程
│   │   │   ├── useBulkConfirm()           # 批量操作确认
│   │   │   └── useDestructiveConfirm()    # 危险操作确认
│   │   ├── useErrorHandler.ts # 错误处理 Hook
│   │   │   ├── useGlobalError()           # 全局错误处理
│   │   │   ├── useAPIError()              # API 错误处理
│   │   │   ├── useValidationError()       # 验证错误处理
│   │   │   ├── useErrorRecovery()         # 错误恢复逻辑
│   │   │   └── useErrorReporting()        # 错误上报功能
│   │   ├── useLocalStorage.ts # 本地存储 Hook
│   │   │   ├── useStoredState()           # 持久化状态 Hook
│   │   │   ├── useStoredQueries()         # 查询历史存储
│   │   │   ├── useStoredSettings()        # 用户设置存储
│   │   │   └── useStoredTheme()           # 主题偏好存储
│   │   ├── useKeyboard.ts   # 键盘交互 Hook
│   │   │   ├── useHotkeys()               # 快捷键处理
│   │   │   ├── useEscapeKey()             # ESC 键处理
│   │   │   ├── useEnterKey()              # 回车键处理
│   │   │   └── useKeyboardNavigation()    # 键盘导航
│   │   └── 🚧 未来扩展 Hooks              # 根据功能需求添加
│       │   ├── useWebSocket.ts           # WebSocket 连接管理
│       │   ├── useChart.ts               # 图表数据管理
│       │   ├── useExport.ts              # 导出功能管理
│       │   ├── useVirtualization.ts      # 虚拟滚动优化
│       │   └── usePerformance.ts         # 性能监控 Hook
│
│   ├── types/              # TypeScript 类型定义
│   │   ├── index.ts        # 主要类型定义导出
│   │   │   ├── Message 接口               # 消息对象类型
│   │   │   ├── ApiResponse<T> 接口        # API 响应类型
│   │   │   ├── TableSchema 接口           # 表结构类型
│   │   │   ├── ColumnInfo 接口            # 列信息类型
│   │   │   ├── QueryResult 接口           # 查询结果类型
│   │   │   └── 基础接口导出               # 类型统一导出
│   │   ├── api.ts          # API 相关类型定义
│   │   │   ├── RequestConfig 接口         # 请求配置类型
│   │   │   ├── ResponseError 接口         # 错误响应类型
│   │   │   ├── PaginationParams 接口      # 分页参数类型
│   │   │   ├── SortParams 接口            # 排序参数类型
│   │   │   └── FilterParams 接口          # 筛选参数类型
│   │   ├── ui.ts           # UI 组件类型定义
│   │   │   ├── ButtonVariants 类型        # 按钮变体类型
│   │   │   ├── ComponentProps<T> 类型     # 组件属性类型
│   │   │   ├── ThemeMode 类型             # 主题模式类型
│   │   │   ├── Size 类型                  # 尺寸规格类型
│   │   │   └── ColorVariant 类型          # 颜色变体类型
│   │   ├── conversation.ts # 对话相关类型定义
│   │   │   ├── ConversationState 接口     # 对话状态类型
│   │   │   ├── MessageRole 类型           # 消息角色枚举
│   │   │   ├── MessageStatus 类型         # 消息状态枚举
│   │   │   ├── TypingState 接口           # 打字状态类型
│   │   │   └── ConversationHistory 接口   # 对话历史类型
│   │   ├── database.ts     # 数据库相关类型定义
│   │   │   ├── DatabaseConnection 接口    # 数据库连接类型
│   │   │   ├── TableMetadata 接口         # 表元数据类型
│   │   │   ├── ColumnType 枚举            # 列数据类型
│   │   │   ├── IndexInfo 接口             # 索引信息类型
│   │   │   └── RelationshipInfo 接口      # 关系信息类型
│   │   └── 🚧 未来扩展类型文件             # 根据功能需求添加
│       │   ├── chart.ts                  # 图表相关类型
│       │   ├── export.ts                 # 导出功能类型
│       │   ├── websocket.ts              # WebSocket 类型
│       │   └── user.ts                   # 用户相关类型 (未来功能)
│
│   └── store/              # 状态管理 (Zustand)
│       ├── index.ts        # ✅ Store 统一导出
│       │   ├── ✅ conversationStore 导出 # 对话状态管理导出
│       │   └── ✅ dataStore 导出         # 数据状态管理导出
│       ├── conversationStore.ts # ✅ 对话状态存储
│       │   ├── ✅ ConversationState 接口 # 对话状态接口
│       │   ├── ✅ messages: Message[]    # 消息数组状态
│       │   ├── ✅ isTyping: boolean      # 打字状态
│       │   ├── ✅ currentInput: string   # 当前输入内容
│       │   ├── ✅ conversationId: string # 对话 ID
│       │   ├── ✅ sendMessage()          # 发送消息动作 (集成LangGraph)
│       │   ├── ✅ addMessage()           # 添加消息动作
│       │   ├── ✅ clearConversation()    # 清空对话动作
│       │   ├── ✅ setTyping()            # 设置打字状态
│       │   ├── ✅ updateInput()          # 更新输入内容
│       │   └── ✅ setConversationId()    # 设置对话 ID
│       ├── dataStore.ts    # ✅ 数据状态存储 (新增)
│       │   ├── ✅ DataState 接口         # 数据状态接口
│       │   ├── ✅ queryResult: QueryResult # 查询结果状态
│       │   ├── ✅ tableData: any[]       # 表格数据状态
│       │   ├── ✅ schema: TableSchema[]  # 数据库结构状态
│       │   ├── ✅ selectedRows: any[]    # 选中行状态
│       │   ├── ✅ sortConfig: object     # 排序配置状态
│       │   ├── ✅ filterConfig: object   # 筛选配置状态
│       │   ├── ✅ pagination: object     # 分页状态
│       │   ├── ✅ setQueryResult()       # 设置查询结果动作
│       │   ├── ✅ setTableData()         # 设置表格数据
│       │   ├── ✅ updateSort()           # 更新排序配置
│       │   ├── ✅ updateFilter()         # 更新筛选配置
│       │   └── ✅ clearData()            # 清空数据动作
│       ├── uiStore.ts      # UI 状态存储
│       │   ├── UIState 接口             # UI 状态接口
│       │   ├── theme: ThemeMode         # 主题模式状态
│       │   ├── sidebarOpen: boolean     # 侧边栏开关状态
│       │   ├── dialogStates: object     # 对话框状态集合
│       │   ├── loadingStates: object    # 加载状态集合
│       │   ├── activeTab: string        # 当前活跃标签
│       │   ├── windowSize: object       # 窗口尺寸状态
│       │   ├── toggleTheme()            # 切换主题动作
│       │   ├── toggleSidebar()          # 切换侧边栏动作
│       │   ├── setDialog()              # 设置对话框状态
│       │   ├── setLoading()             # 设置加载状态
│       │   ├── setActiveTab()           # 设置活跃标签
│       │   └── updateWindowSize()       # 更新窗口尺寸
│       ├── dataStore.ts    # 数据状态存储
│       │   ├── DataState 接口           # 数据状态接口
│       │   ├── tableData: any[]         # 表格数据状态
│       │   ├── schema: TableSchema[]    # 数据库结构状态
│       │   ├── queryResult: QueryResult # 查询结果状态
│       │   ├── selectedRows: any[]      # 选中行状态
│       │   ├── sortConfig: object       # 排序配置状态
│       │   ├── filterConfig: object     # 筛选配置状态
│       │   ├── pagination: object       # 分页状态
│       │   ├── setTableData()           # 设置表格数据动作
│       │   ├── setSchema()              # 设置数据库结构
│       │   ├── setQueryResult()         # 设置查询结果
│       │   ├── setSelectedRows()        # 设置选中行
│       │   ├── updateSort()             # 更新排序配置
│       │   ├── updateFilter()           # 更新筛选配置
│       │   └── updatePagination()       # 更新分页状态
│       ├── apiStore.ts     # API 调用状态存储
│       │   ├── APIState 接口            # API 状态接口
│       │   ├── requestStates: object    # 请求状态集合
│       │   ├── errors: object           # 错误状态集合
│       │   ├── cache: object            # API 缓存状态
│       │   ├── connectionStatus: string # 连接状态
│       │   ├── setRequestState()        # 设置请求状态动作
│       │   ├── setError()               # 设置错误状态
│       │   ├── clearError()             # 清除错误状态
│       │   ├── updateCache()            # 更新缓存动作
│       │   ├── setConnectionStatus()    # 设置连接状态
│       │   └── clearCache()             # 清除缓存动作
│       └── 🚧 未来扩展 Store            # 根据功能需求添加
│           ├── chartStore.ts           # 图表状态存储
│           ├── exportStore.ts          # 导出功能状态存储
│           ├── userStore.ts            # 用户状态存储 (未来功能)
│           └── settingsStore.ts        # 设置状态存储
│
├── public/                 # 静态资源目录
│   ├── favicon.ico         # 网站图标
│   ├── logo.svg            # 应用 Logo
│   ├── images/             # 图片资源
│   │   ├── placeholder.png         # 占位图片
│   │   ├── error-states/           # 错误状态图片
│   │   ├── illustrations/          # 插画素材
│   │   └── icons/                  # 图标素材
│   ├── fonts/              # 字体文件 (如果需要本地字体)
│   │   └── custom-fonts/           # 自定义字体文件
│   └── manifest.json       # PWA 应用清单 (未来功能)
│
├── package.json            # 项目依赖和脚本配置
│   ├── dependencies                # 生产依赖包
│   │   ├── next: ^14.2.15          # Next.js 框架
│   │   ├── react: ^18.2.0          # React 库
│   │   ├── react-dom: ^18.2.0      # React DOM
│   │   ├── typescript: ^5.4.0      # TypeScript
│   │   ├── axios: ^1.6.0           # HTTP 客户端
│   │   ├── zustand: ^4.4.0         # 状态管理
│   │   ├── lucide-react: ^0.400.0  # 图标库
│   │   ├── clsx: ^2.1.0            # 条件类名工具
│   │   └── tailwind-merge: ^2.3.0  # Tailwind 类名合并
│   ├── devDependencies             # 开发依赖包
│   │   ├── @types/node: ^20.0.0    # Node.js 类型定义
│   │   ├── @types/react: ^18.0.0   # React 类型定义
│   │   ├── eslint: ^8.0.0          # 代码检查工具
│   │   ├── prettier: ^3.0.0        # 代码格式化工具
│   │   ├── tailwindcss: ^3.4.0     # Tailwind CSS
│   │   └── autoprefixer: ^10.4.0   # CSS 前缀自动添加
│   └── scripts                     # NPM 脚本
│       ├── dev: "next dev"         # 开发服务器
│       ├── build: "next build"     # 生产构建
│       ├── start: "next start"     # 生产服务器
│       └── lint: "next lint"       # 代码检查
│
├── next.config.js          # Next.js 配置文件
│   ├── reactStrictMode: true       # React 严格模式
│   ├── rewrites() 配置             # API 代理配置
│   │   └── /api/backend/* → http://localhost:5003/* # 后端代理规则
│   ├── images 配置                 # 图片优化配置
│   └── experimental 配置           # 实验性功能配置
│
├── tailwind.config.js      # Tailwind CSS 配置文件
│   ├── content 配置                # 内容路径配置
│   ├── theme 扩展配置              # 主题自定义配置
│   │   ├── colors (CSS 变量映射)   # 颜色系统配置
│   │   ├── borderRadius           # 圆角配置
│   │   ├── keyframes              # 动画关键帧
│   │   └── animation              # 动画配置
│   ├── plugins 配置                # 插件配置
│   │   └── tailwindcss-animate    # 动画插件
│   └── darkMode: ["class"]         # 深色模式配置
│
├── tsconfig.json           # TypeScript 配置文件
│   ├── compilerOptions             # 编译选项配置
│   │   ├── strict: true           # 严格模式
│   │   ├── moduleResolution       # 模块解析策略
│   │   ├── jsx: "preserve"        # JSX 保留模式
│   │   └── paths 路径映射         # 路径别名配置
│   ├── include 文件包含规则        # 包含的文件类型
│   └── exclude 文件排除规则        # 排除的目录
│
├── postcss.config.js       # PostCSS 配置文件
│   ├── tailwindcss 插件            # Tailwind CSS 处理
│   └── autoprefixer 插件           # 浏览器前缀自动添加
│
├── .eslintrc.json          # ESLint 配置文件
│   └── extends: ["next/core-web-vitals"] # Next.js 推荐规则
│
├── .gitignore              # Git 忽略文件配置
│   ├── node_modules/              # 依赖包目录
│   ├── .next/                     # Next.js 构建目录
│   ├── out/                       # 导出目录
│   ├── .env.local                 # 环境变量文件
│   └── 其他构建产物               # 临时文件和日志
│
├── next-env.d.ts           # Next.js 环境类型定义
│   └── Next.js 和图像类型引用     # 框架类型定义
│
├── package-lock.json       # 依赖锁定文件 (NPM)
│   └── 精确的依赖版本锁定         # 确保构建一致性
│
└── README.md               # 项目说明文档
    ├── 项目概述                   # 项目介绍
    ├── 快速开始指南               # 安装和运行说明
    ├── 技术栈说明                 # 技术选型说明
    ├── 项目结构说明               # 目录结构介绍
    ├── 开发指南                   # 开发规范和流程
    ├── API 集成说明               # 后端集成说明
    └── 部署指南                   # 生产部署说明

# --- 未来扩展目录 (根据功能需求逐步添加) ---
# tests/                    # 测试文件目录
# ├── __tests__/           # 单元测试
# ├── e2e/                 # 端到端测试
# └── utils/               # 测试工具函数

# docs/                    # 项目文档目录
# ├── development.md       # 开发文档
# ├── deployment.md        # 部署文档
# └── api-reference.md     # API 参考文档

# .github/                 # GitHub 工作流配置
# └── workflows/           # CI/CD 工作流文件
#     ├── test.yml         # 测试工作流
#     ├── build.yml        # 构建工作流
#     └── deploy.yml       # 部署工作流 

## 📊 项目实现状态 (2025-01-31 更新)

### ✅ 已完成组件
```
src/
├── app/
│   ├── layout.tsx          ✅ 实现 - 根布局，字体配置，元数据
│   ├── page.tsx            ✅ 实现 - 优化的双栏布局，集成TableDisplay
│   └── globals.css         ✅ 实现 - 主题变量，自定义滚动条，基础样式
├── components/
│   ├── ui/                 ✅ 部分实现
│   │   ├── button.tsx      ✅ 完整实现 - 多变体按钮组件
│   │   ├── input.tsx       ✅ 完整实现 - 表单输入组件
│   │   ├── card.tsx        ✅ 完整实现 - 容器卡片组件
│   │   └── table.tsx       ✅ 完整实现 - Shadcn/ui表格组件
│   ├── chat/               ✅ 完整实现
│   │   ├── ChatInterface.tsx    ✅ 聊天主界面容器，布局优化
│   │   ├── MessageList.tsx      ✅ 消息列表，滚动控制，数据解析集成
│   │   ├── MessageBubble.tsx    ✅ 用户/AI消息气泡，时间戳
│   │   ├── InputArea.tsx        ✅ 输入区域，快捷键，验证
│   │   └── TypingIndicator.tsx  ✅ 打字指示器，CSS动画
│   └── data/               ✅ 新增实现
│       └── TableDisplay.tsx     ✅ 完整实现 - TanStack Table集成，数据展示
├── lib/
│   ├── api.ts              ✅ 完整实现 - 后端集成，超时配置，错误处理
│   ├── dataParser.ts       ✅ 完整实现 - 聊天消息数据解析工具
│   └── utils.ts            ✅ 实现 - 类名合并工具
├── types/
│   └── index.ts            ✅ 实现 - 基础类型定义 (Message, QueryResult等)
└── store/
    ├── conversationStore.ts ✅ 完整实现 - 对话状态，错误处理
    ├── dataStore.ts        ✅ 完整实现 - 数据状态管理，表格控制
    └── index.ts            ✅ 实现 - Store统一导出
```

### 🚧 待开发组件
```
components/
├── ui/                     📋 计划中
│   ├── dialog.tsx          🔄 下个阶段 (确认流程需要)
│   ├── badge.tsx           📋 待规划
│   └── ...                 📋 根据需求添加
├── data/                   ✅ 核心功能完成
│   ├── SchemaView.tsx      ✅ 已完成 (数据库结构展示 + API修复) 🆕
│   ├── TableDisplay.tsx    ✅ 已完成 (数据表格展示)
│   ├── PreviewCard.tsx     🔄 计划开发 (操作预览)
│   └── ResultFormatter.tsx 📋 待规划 (结果格式化)
├── dialogs/                📋 后续阶段
│   ├── ConfirmationDialog.tsx 🔄 确认流程需要
│   ├── ErrorDialog.tsx     📋 错误展示优化
│   └── LoadingDialog.tsx   📋 长时间操作
└── layout/                 📋 扩展功能
    ├── Header.tsx          📋 导航栏
    ├── Sidebar.tsx         📋 功能面板
    └── Footer.tsx          📋 状态信息
```

### 🎯 技术栈实现状态

| 技术 | 状态 | 版本 | 配置状态 |
|------|------|------|----------|
| **Next.js** | ✅ | 14.2.15 | App Router配置完整 |
| **React** | ✅ | 18.2.0 | hooks，组件，状态管理完整 |
| **TypeScript** | ✅ | 5.4+ | 类型系统，路径别名完整 |
| **Tailwind CSS** | ✅ | 3.4+ | 主题，组件样式，响应式完整 |
| **Zustand** | ✅ | 4.4+ | 对话状态完整，扩展状态计划中 |
| **Axios** | ✅ | 1.6+ | 拦截器，超时配置，错误处理 |
| **Lucide React** | ✅ | 0.400+ | 图标组件集成完整 |

### 📈 下一步开发计划

#### ✅ 已完成功能 (短期目标达成)
1. **SchemaView 组件** ✅
   - 数据库结构可视化
   - 表列表和字段详情展示
   - 实时记录数统计
   - 搜索和折叠导航功能
   - 字段类型颜色标识
   - 主键和索引标识

2. **TableDisplay 组件** ✅
   - 数据表格展示查询结果
   - 排序、筛选、分页功能
   - 响应式表格设计

3. **数据状态管理** ✅
   - dataStore.ts 完整实现
   - 查询结果状态管理
   - Schema数据管理

#### 🔄 中优先级 (后续阶段)
1. **确认流程对话框**
   - 操作预览和确认
   - 批量操作支持
   - 错误恢复机制

2. **UI 组件库扩展**
   - Table、Dialog、Badge 等
   - 统一设计系统
   - 可访问性支持

3. **高级功能**
   - 数据导出功能
   - 图表可视化
   - 操作历史记录

---

**文档版本**: v5.0  
**最后更新**: 2025-05-26 22:00  
**实现进度**: 数据库结构展示功能完成！SchemaView组件已实现并修复API数据格式问题，功能完全正常 