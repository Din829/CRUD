import { create } from 'zustand'
import type { QueryResult, TableSchema } from '@/types'

/**
 * 数据状态接口
 */
interface DataState {
  // 数据状态
  queryResult: QueryResult | null
  tableData: Record<string, any>[]
  schema: TableSchema[]
  isLoading: boolean
  error: string | null
  
  // 表格控制状态
  selectedRows: Record<string, any>[]
  sortConfig: {
    key: string
    direction: 'asc' | 'desc'
  } | null
  filterConfig: Record<string, any>
  pagination: {
    pageIndex: number
    pageSize: number
    total: number
  }
  
  // 动作方法
  setQueryResult: (result: QueryResult | null) => void
  setTableData: (data: Record<string, any>[]) => void
  setSchema: (schema: TableSchema[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  
  // 表格控制方法
  setSelectedRows: (rows: Record<string, any>[]) => void
  updateSort: (key: string, direction: 'asc' | 'desc') => void
  updateFilter: (filters: Record<string, any>) => void
  updatePagination: (pagination: Partial<DataState['pagination']>) => void
  
  // 重置方法
  clearData: () => void
  reset: () => void
}

/**
 * 初始状态
 */
const initialState = {
  queryResult: null,
  tableData: [],
  schema: [],
  isLoading: false,
  error: null,
  selectedRows: [],
  sortConfig: null,
  filterConfig: {},
  pagination: {
    pageIndex: 0,
    pageSize: 10,
    total: 0
  }
}

/**
 * 数据状态管理 Store
 */
export const useDataStore = create<DataState>((set, get) => ({
  ...initialState,
  
  // 设置查询结果
  setQueryResult: (result) => {
    set({ 
      queryResult: result,
      tableData: result?.rows || [],
      pagination: {
        ...get().pagination,
        total: result?.total || 0
      }
    })
  },
  
  // 设置表格数据
  setTableData: (data) => {
    set({ 
      tableData: data,
      pagination: {
        ...get().pagination,
        total: data.length
      }
    })
  },
  
  // 设置数据库结构
  setSchema: (schema) => set({ schema }),
  
  // 设置加载状态
  setLoading: (loading) => set({ isLoading: loading }),
  
  // 设置错误信息
  setError: (error) => set({ error }),
  
  // 设置选中行
  setSelectedRows: (rows) => set({ selectedRows: rows }),
  
  // 更新排序配置
  updateSort: (key, direction) => {
    set({ sortConfig: { key, direction } })
  },
  
  // 更新筛选配置
  updateFilter: (filters) => {
    set({ filterConfig: { ...get().filterConfig, ...filters } })
  },
  
  // 更新分页配置
  updatePagination: (pagination) => {
    set({ 
      pagination: { ...get().pagination, ...pagination }
    })
  },
  
  // 清空数据
  clearData: () => {
    set({
      queryResult: null,
      tableData: [],
      selectedRows: [],
      error: null
    })
  },
  
  // 重置所有状态
  reset: () => set(initialState)
})) 