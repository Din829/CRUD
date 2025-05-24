/**
 * 消息类型定义
 */
export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
}

/**
 * API 响应基础类型
 */
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

/**
 * 数据库表结构类型
 */
export interface TableSchema {
  name: string
  columns: ColumnInfo[]
}

export interface ColumnInfo {
  name: string
  type: string
  nullable: boolean
  key: string
  default?: any
}

/**
 * 查询结果类型
 */
export interface QueryResult {
  columns: string[]
  rows: Record<string, any>[]
  total: number
} 