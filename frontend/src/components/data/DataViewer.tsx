'use client'

import React, { useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDataStore } from '@/store'
import { Table, RefreshCw, Database, Search, ChevronLeft, ChevronRight } from 'lucide-react'
import {
  Table as UITable,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface DataViewerProps {
  selectedTable: string | null
}

/**
 * DataViewer 组件 - 数据库表数据查看器
 */
export function DataViewer({ selectedTable }: DataViewerProps) {
  const {
    tableViewData,
    tableViewLoading,
    tableViewError,
    tableViewPagination,
    loadTableData,
    setTableViewPagination
  } = useDataStore()

  // 当选中表变化时，加载数据
  useEffect(() => {
    if (selectedTable) {
      loadTableData(selectedTable, 1)
    }
  }, [selectedTable, loadTableData])

  // 格式化数据值显示
  const formatValue = (value: any) => {
    if (value === null || value === undefined) {
      return <span className="text-muted-foreground italic">NULL</span>
    }
    
    if (typeof value === 'boolean') {
      return <span className={value ? 'text-green-600' : 'text-red-600'}>
        {value ? '是' : '否'}
      </span>
    }
    
    if (typeof value === 'number') {
      return <span className="font-mono">{value.toLocaleString()}</span>
    }
    
    if (typeof value === 'string') {
      if (value.length > 100) {
        return (
          <span title={value} className="truncate block max-w-[200px]">
            {value.substring(0, 100)}...
          </span>
        )
      }
      return <span>{value}</span>
    }
    
    return <span>{String(value)}</span>
  }

  // 处理分页变化
  const handlePageChange = (newPage: number) => {
    if (selectedTable && newPage >= 1 && newPage <= tableViewPagination.totalPages) {
      loadTableData(selectedTable, newPage)
    }
  }

  // 处理刷新
  const handleRefresh = () => {
    if (selectedTable) {
      loadTableData(selectedTable, tableViewPagination.page)
    }
  }

  // 如果没有选中表
  if (!selectedTable) {
    return (
      <Card className="h-full flex flex-col">
        <CardHeader className="flex-shrink-0 pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Database className="h-5 w-5" />
            表数据查看器
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 overflow-hidden flex items-center justify-center">
          <div className="text-center text-muted-foreground">
            <Database className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
            <p className="text-base mb-2">请选择一个表</p>
            <p className="text-sm">点击左侧数据库结构中的表名查看数据</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // 加载状态
  if (tableViewLoading) {
    return (
      <Card className="h-full flex flex-col">
        <CardHeader className="flex-shrink-0 pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Table className="h-5 w-5" />
            {selectedTable}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 overflow-hidden flex items-center justify-center">
          <div className="text-center">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2 text-primary" />
            <p className="text-sm text-muted-foreground">加载表数据中...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // 错误状态
  if (tableViewError) {
    return (
      <Card className="h-full flex flex-col">
        <CardHeader className="flex-shrink-0 pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Table className="h-5 w-5" />
            {selectedTable}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 overflow-hidden flex items-center justify-center">
          <div className="text-center">
            <p className="text-sm text-red-600 mb-2">加载失败</p>
            <p className="text-xs text-muted-foreground mb-4">{tableViewError}</p>
            <Button onClick={handleRefresh} size="sm">
              重试
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  // 获取列名
  const columns = tableViewData.length > 0 ? Object.keys(tableViewData[0]) : []

  return (
    <Card className="h-full flex flex-col">
      {/* 头部 */}
      <CardHeader className="flex-shrink-0 pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Table className="h-5 w-5" />
            {selectedTable}
            <span className="text-sm font-normal text-muted-foreground">
              ({tableViewPagination.total.toLocaleString()} 条记录)
            </span>
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button onClick={handleRefresh} size="sm" variant="outline">
              <RefreshCw className="h-4 w-4 mr-1" />
              刷新
            </Button>
          </div>
        </div>
      </CardHeader>

      {/* 表格内容 */}
      <CardContent className="flex-1 min-h-0 overflow-hidden p-4 space-y-4">
        {tableViewData.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-muted-foreground">
              <p className="text-base mb-2">表为空</p>
              <p className="text-sm">该表暂无数据记录</p>
            </div>
          </div>
        ) : (
          <>
            {/* 表格 */}
            <div className="flex-1 overflow-auto rounded-md border">
              <UITable>
                <TableHeader>
                  <TableRow>
                    {columns.map((column) => (
                      <TableHead key={column} className="font-medium whitespace-nowrap">
                        {column}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tableViewData.map((row, index) => (
                    <TableRow key={index} className="hover:bg-muted/50">
                      {columns.map((column) => (
                        <TableCell key={column} className="py-2 max-w-[200px]">
                          {formatValue(row[column])}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </UITable>
            </div>

            {/* 分页控件 */}
            {tableViewPagination.totalPages > 1 && (
              <div className="flex items-center justify-between text-sm">
                <div className="text-muted-foreground">
                  第 {((tableViewPagination.page - 1) * tableViewPagination.limit + 1).toLocaleString()} - {Math.min(tableViewPagination.page * tableViewPagination.limit, tableViewPagination.total).toLocaleString()} 条，
                  共 {tableViewPagination.total.toLocaleString()} 条记录
                </div>
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(tableViewPagination.page - 1)}
                    disabled={tableViewPagination.page <= 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    上一页
                  </Button>
                  <div className="text-muted-foreground">
                    第 {tableViewPagination.page} 页，共 {tableViewPagination.totalPages} 页
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(tableViewPagination.page + 1)}
                    disabled={tableViewPagination.page >= tableViewPagination.totalPages}
                  >
                    下一页
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
} 