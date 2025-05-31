# DifyLang 前端架构

## 🏗️ 项目结构

```
frontend/
├── src/                    # 前端源代码
│   ├── app/                # Next.js 14 App Router
│   │   ├── layout.tsx      # 根布局组件 ✅
│   │   ├── page.tsx        # 主页面 (50-50布局) ✅
│   │   └── globals.css     # 全局样式 + 主题变量 ✅
│   │
│   ├── components/         # React 组件库
│   │   ├── ui/             # 基础 UI 组件 (Shadcn/ui) ✅
│   │   │   ├── button.tsx           # 按钮组件
│   │   │   ├── input.tsx            # 输入框组件
│   │   │   ├── card.tsx             # 卡片组件
│   │   │   ├── table.tsx            # 表格组件
│   │   │   └── dialog.tsx           # 对话框组件
│   │   │
│   │   ├── chat/           # 聊天功能组件 ✅
│   │   │   ├── ChatInterface.tsx    # 聊天主界面容器
│   │   │   ├── MessageList.tsx      # 消息列表 + 数据解析
│   │   │   ├── MessageBubble.tsx    # 消息气泡 + 确认流程
│   │   │   ├── InputArea.tsx        # 输入区域 + 快捷键
│   │   │   └── TypingIndicator.tsx  # 打字指示器
│   │   │
│   │   ├── data/           # 数据展示组件 ✅
│   │   │   ├── TableDisplay.tsx     # TanStack Table 数据展示
│   │   │   └── SchemaView.tsx       # 数据库结构可视化
│   │   │
│   │   └── dialogs/        # 对话框组件 ✅
│   │       └── ConfirmationDialog.tsx # 确认对话框
│   │
│   ├── lib/                # 工具库和核心服务 ✅
│   │   ├── api.ts          # API 客户端 (Axios + LangGraph集成)
│   │   ├── dataParser.ts   # 数据解析工具 (从聊天消息提取数据)
│   │   └── utils.ts        # 通用工具函数
│   │
│   ├── hooks/              # React 自定义 Hooks ✅
│   │   └── useConfirmation.ts # 确认流程管理 Hook
│   │
│   ├── types/              # TypeScript 类型定义 ✅
│   │   └── index.ts        # 主要类型定义 (Message, QueryResult, etc.)
│   │
│   └── store/              # 状态管理 (Zustand) ✅
│       ├── conversationStore.ts # 对话状态管理
│       ├── dataStore.ts        # 数据状态管理
│       └── index.ts            # Store 统一导出
│
├── public/                 # 静态资源
├── package.json            # 项目依赖 (396 packages, 0 vulnerabilities)
├── next.config.js          # Next.js 配置 (API代理)
├── tailwind.config.js      # Tailwind 配置 (主题系统)
└── tsconfig.json           # TypeScript 配置
```

## 🎯 核心功能模块

### 1. 聊天界面模块 ✅
- **ChatInterface**: 主要聊天容器，集成所有聊天组件
- **MessageList**: 消息历史展示，集成数据解析和自动滚动
- **MessageBubble**: 用户/AI消息气泡，支持确认流程交互
- **InputArea**: 输入框和发送按钮，支持 Enter 快捷键
- **TypingIndicator**: AI 思考指示器，CSS 动画效果

### 2. 数据展示模块 ✅
- **TableDisplay**: TanStack Table 集成，查询结果展示
  - 动态列生成，排序、搜索、分页功能
  - 智能数据格式化，响应式表格设计
- **SchemaView**: 数据库结构可视化
  - 表列表展示，字段详情，实时统计
  - 搜索功能，折叠/展开导航

### 3. 确认流程模块 ✅
- **ConfirmationDialog**: 操作确认对话框
- **MessageBubble集成**: 智能识别确认消息，显示交互按钮
- **多操作支持**: 修改/新增/删除/复合操作

### 4. 状态管理模块 ✅
- **ConversationStore**: 对话状态，会话ID管理
- **DataStore**: 数据状态，查询结果和表格状态
- **全局状态**: Zustand 轻量级状态管理

### 5. API 集成模块 ✅
- **API Client**: 统一 LangGraph 后端通信
- **错误处理**: 智能错误分类和用户提示
- **超时配置**: 90秒聊天，60秒其他接口
- **会话管理**: 持久化 session 状态

## 📱 UI/UX 设计

### 布局设计 ✅
```
┌─────────────────────────────────────┐
│  Chat Area (50%)   │  Data Panel (50%) │
│  ┌─────────────────┬─────────────────┐ │
│  │ Messages        │ TableDisplay    │ │
│  │ + Input         │ + SchemaView    │ │
│  │ + Typing        │ + QueryResults  │ │
│  └─────────────────┴─────────────────┘ │
└─────────────────────────────────────┘
```

### 交互模式 ✅
- **对话式**: ChatGPT 风格的聊天界面
- **即时反馈**: 实时状态更新和错误提示
- **智能识别**: 自动数据解析和确认流程

## 🚀 技术栈

### 核心技术 ✅
- **Next.js 14.2**: App Router, TypeScript 5.4+
- **React 18.2**: Hooks, 状态管理
- **Tailwind CSS 3.4**: 原子化 CSS + 主题系统
- **Shadcn/ui**: 现代化组件库
- **Zustand 4.4**: 轻量级状态管理
- **Axios 1.6**: HTTP 客户端
- **TanStack Table**: 数据表格
- **Lucide React**: 图标库

### 开发配置 ✅
- **环境**: Node.js 18+, npm
- **构建**: Next.js 生产构建
- **类型检查**: TypeScript 严格模式
- **代码检查**: ESLint + Next.js 规则
- **API代理**: `/api/backend/*` → `localhost:5003/*`

## 🎉 完成功能

### ✅ 已实现功能
```
✅ 基础架构        - Next.js + TypeScript + Tailwind
✅ 聊天界面        - 完整的对话功能
✅ 数据展示        - 表格 + 数据库结构展示  
✅ 确认流程        - 操作确认和执行
✅ 状态管理        - 对话状态 + 数据状态
✅ API 集成        - LangGraph 后端完全集成
✅ 错误处理        - 友好的用户提示
✅ 布局优化        - 响应式50-50布局
```




## 📊 实现状态总结

**项目状态**: ✅ 核心功能完成，可用于演示  
**技术债务**: 0 critical issues  
**文件数量**: 20+ 组件，完整架构  
**测试状态**: 集成功能验证通过  

**下一步**: 功能扩展和用户体验优化

---

**文档版本**: v2.0  
**最后更新**: 2025-05-31  
**状态**: 前端确认流程完全正常，架构稳定 🎉 