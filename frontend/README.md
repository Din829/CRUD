# DifyLang Frontend

基于 Next.js 14 的智能数据库操作平台前端应用。

## 🚀 快速开始

### 环境要求

- Node.js 18+
- npm/yarn/pnpm

### 安装依赖

```bash
npm install
```

### 环境配置

创建 `.env.local` 文件：

```env
# 后端 API 基础 URL
NEXT_PUBLIC_API_BASE_URL=http://localhost:5003

# 应用名称
NEXT_PUBLIC_APP_NAME=DifyLang

# 开发模式
NODE_ENV=development
```

### 启动开发服务器

```bash
npm run dev
```

应用将在 [http://localhost:3000](http://localhost:3000) 启动。

### 构建生产版本

```bash
npm run build
npm start
```

## 🏗️ 项目结构

```
src/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # 根布局
│   ├── page.tsx           # 首页
│   └── globals.css        # 全局样式
├── components/            # React 组件
│   ├── ui/               # 基础 UI 组件
│   ├── chat/             # 聊天相关组件
│   ├── data/             # 数据展示组件
│   ├── dialogs/          # 对话框组件
│   └── layout/           # 布局组件
├── lib/                  # 工具库
│   ├── api.ts           # API 客户端
│   └── utils.ts         # 工具函数
├── hooks/               # React Hooks
├── types/               # TypeScript 类型定义
└── store/               # 状态管理
```

## 🎨 技术栈

- **框架**: Next.js 14 (App Router)
- **UI 库**: React 18
- **类型系统**: TypeScript
- **样式**: Tailwind CSS + Shadcn/ui
- **状态管理**: Zustand
- **HTTP 客户端**: Axios
- **图标**: Lucide React

## 🔧 开发工具

- **代码检查**: ESLint
- **代码格式化**: Prettier
- **样式处理**: PostCSS + Autoprefixer

## 📡 API 集成

前端通过 Next.js 的 rewrites 功能代理后端 API：

- 前端路径: `/api/backend/*`
- 后端地址: `http://localhost:5003/*`

## 🚀 部署

推荐使用 Vercel 进行部署：

```bash
npm run build
```

或直接连接 Git 仓库到 Vercel 进行自动部署。 