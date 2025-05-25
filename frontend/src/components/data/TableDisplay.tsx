'use client'

import React from 'react'
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDataStore } from '@/store'

interface TableDisplayProps {
  data?: Record<string, any>[]
  columns?: string[]
  title?: string
  searchable?: boolean
  paginated?: boolean
}

/**
 * 动态生成列定义
 */
function generateColumns(data: Record<string, any>[], columns?: string[]): ColumnDef<any>[] {
  if (!data || data.length === 0) return []
  
  const firstRow = data[0]
  const keys = columns || Object.keys(firstRow)
  
  return keys.map((key) => ({
    accessorKey: key,
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          className="h-auto p-0 font-medium hover:bg-transparent"
        >
          {key.charAt(0).toUpperCase() + key.slice(1)}
          {column.getIsSorted() === "asc" ? " ↑" : column.getIsSorted() === "desc" ? " ↓" : ""}
        </Button>
      )
    },
    cell: ({ row }) => {
      const value = row.getValue(key)
      
      // 格式化不同类型的数据
      if (value === null || value === undefined) {
        return <span className="text-muted-foreground">-</span>
      }
      
      if (typeof value === 'boolean') {
        return <span className={value ? 'text-green-600' : 'text-red-600'}>
          {value ? '是' : '否'}
        </span>
      }
      
      if (typeof value === 'number') {
        return <span className="font-mono">{value.toLocaleString()}</span>
      }
      
      if (typeof value === 'string' && value.length > 50) {
        return (
          <span title={value} className="truncate block max-w-[200px]">
            {value}
          </span>
        )
      }
      
      return <span>{String(value)}</span>
    },
  }))
}

/**
 * TableDisplay 组件
 */
export function TableDisplay({ 
  data: propData, 
  columns: propColumns,
  title = "数据表格",
  searchable = true,
  paginated = true
}: TableDisplayProps) {
  const { tableData, isLoading, error } = useDataStore()
  
  // 使用传入的数据或store中的数据
  const data = propData || tableData
  const columns = React.useMemo(() => generateColumns(data, propColumns), [data, propColumns])
  
  // 表格状态
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({})
  const [globalFilter, setGlobalFilter] = React.useState('')
  
  // 创建表格实例
  const table = useReactTable({
    data,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: 'includesString',
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      globalFilter,
    },
    initialState: {
      pagination: {
        pageSize: 10,
      },
    },
  })
  
  // 加载状态
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
          <p className="text-sm text-muted-foreground">加载中...</p>
        </div>
      </div>
    )
  }
  
  // 错误状态
  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-sm text-red-600 mb-2">加载失败</p>
          <p className="text-xs text-muted-foreground">{error}</p>
        </div>
      </div>
    )
  }
  
  // 无数据状态
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-sm text-muted-foreground">暂无数据</p>
          <p className="text-xs text-muted-foreground mt-1">
            请在左侧聊天区域发送查询请求
          </p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="space-y-4">
      {/* 标题和搜索 */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">{title}</h3>
        {searchable && (
          <Input
            placeholder="搜索数据..."
            value={globalFilter ?? ''}
            onChange={(event) => setGlobalFilter(String(event.target.value))}
            className="max-w-sm"
          />
        )}
      </div>
      
      {/* 表格 */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead key={header.id} className="font-medium">
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </TableHead>
                  )
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                  className="hover:bg-muted/50"
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center"
                >
                  没有找到数据
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      
      {/* 分页控件 */}
      {paginated && (
        <div className="flex items-center justify-between space-x-2 py-4">
          <div className="text-sm text-muted-foreground">
            共 {table.getFilteredRowModel().rows.length} 条记录
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              上一页
            </Button>
            <div className="text-sm text-muted-foreground">
              第 {table.getState().pagination.pageIndex + 1} 页，共{' '}
              {table.getPageCount()} 页
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              下一页
            </Button>
          </div>
        </div>
      )}
    </div>
  )
} 