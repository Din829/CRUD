# 数据库管理工具界面实现计划

## 🎯 目标效果
实现类似数据库管理工具的界面：
- 左侧：数据库结构树形视图
- 右侧：选中表的数据实时展示（只读）

## 📋 实现步骤

### 阶段一：基础功能实现

#### 1. 创建新的数据查看器组件
```typescript
// frontend/src/components/data/DataViewer.tsx
interface DataViewerProps {
  selectedTable: string | null
}

功能：
- 接收选中的表名
- 自动查询表数据
- 展示表格数据
- 加载状态处理
```

#### 2. 增强SchemaView组件
```typescript
// 添加表名点击事件
const handleTableClick = (tableName: string) => {
  onTableSelect(tableName) // 通知父组件
}

// 高亮显示选中的表
className={selectedTable === tableName ? 'bg-blue-50' : ''}
```

#### 3. 修改主页面布局
```typescript
// frontend/src/app/page.tsx
const [selectedTable, setSelectedTable] = useState<string | null>(null)

右侧区域：
- 上半部分：SchemaView (可折叠)
- 下半部分：DataViewer (主要区域)
```

#### 4. 添加数据获取逻辑
```typescript
// frontend/src/lib/api.ts
static async getTableData(tableName: string, page = 1, limit = 50) {
  const offset = (page - 1) * limit
  const query = `SELECT * FROM \`${tableName}\` LIMIT ${limit} OFFSET ${offset}`
  return await this.executeQuery(query)
}
```

### 阶段二：用户体验优化

#### 1. 智能分页
- 大表(>1000记录)自动分页
- 小表(<100记录)全量显示
- 分页控件集成

#### 2. 实时搜索
- 表内数据搜索
- 字段级筛选
- 搜索结果高亮

#### 3. 数据统计
- 显示总记录数
- 各字段的数据类型统计
- NULL值比例显示

#### 4. 视觉优化
- 表格斑马纹
- 字段类型图标
- 数据类型颜色编码

## 🔧 技术实现要点

### 性能优化
```typescript
// 1. 防抖查询
const debouncedTableSelect = useDebouncedCallback((tableName: string) => {
  fetchTableData(tableName)
}, 300)

// 2. 缓存机制  
const tableDataCache = new Map<string, CachedData>()

// 3. 虚拟滚动 (对于大数据集)
import { FixedSizeList as List } from 'react-window'
```

### 错误处理
```typescript
// 1. 网络错误处理
// 2. 表不存在处理
// 3. 权限错误处理
// 4. 超时处理
```

### 状态管理
```typescript
// 扩展dataStore
interface DataState {
  selectedTable: string | null
  tableDataCache: Map<string, TableData>
  tableListData: Map<string, Record<string, any>[]>
  setSelectedTable: (table: string | null) => void
  getTableData: (table: string) => Promise<void>
}
```

## 📊 预期效果

### 用户体验
1. **即时响应** - 点击表名立即加载数据
2. **流畅交互** - 表格排序、搜索、分页流畅
3. **视觉直观** - 数据类型一目了然
4. **操作简单** - 无需输入SQL，点击即可查看

### 技术效果
1. **性能优良** - 大表分页加载，小表缓存
2. **错误友好** - 完善的错误提示和处理
3. **扩展性强** - 后续可轻松添加更多功能

## 🕒 开发时间估算

- **阶段一基础功能**: 2-3小时
- **阶段二体验优化**: 3-4小时
- **测试和调优**: 1-2小时

**总计**: 6-9小时可完成完整功能

## 🎉 成果展示

完成后将实现：
```
┌─────────────────────────────────────┐
│  左侧: 数据库结构    │  右侧: 表数据展示   │
│  ├─📊 users (选中)   │  ┌─────────────────┐ │
│  ├─📊 orders        │  │ id │name │email │ │  
│  ├─📊 products      │  │ 1  │张三  │zh@..│ │
│  └─📊 categories    │  │ 2  │李四  │li@..│ │
│                     │  └─────────────────┘ │
│                     │  [1] [2] [3] ... [10]│
└─────────────────────────────────────┘
```

这将是一个专业级的数据库查看工具！ 