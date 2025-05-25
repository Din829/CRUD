'use client'

import React, { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ApiClient } from '@/lib/api'
import { useDataStore } from '@/store'
import { ChevronDown, ChevronRight, Database, Table, Key, Search, RefreshCw } from 'lucide-react'

interface ParsedSchema {
  [tableName: string]: {
    fields: {
      [fieldName: string]: {
        type: string
        null: string
        key: string
        default: any
      }
    }
    foreign_keys?: Record<string, any>
  }
}

interface TableInfo {
  name: string
  fields: Array<{
    name: string
    type: string
    nullable: boolean
    isPrimary: boolean
    isIndex: boolean
    default: any
  }>
  recordCount?: number
}

/**
 * SchemaView 组件 - 数据库结构可视化
 */
export function SchemaView() {
  const { schema, setSchema, setLoading, setError, isLoading, error } = useDataStore()
  const [tables, setTables] = useState<TableInfo[]>([])
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set())
  const [searchTerm, setSearchTerm] = useState('')
  const [filteredTables, setFilteredTables] = useState<TableInfo[]>([])

  // 解析后端返回的schema数据
  const parseSchemaData = (rawSchema: any[]): TableInfo[] => {
    if (!rawSchema || rawSchema.length === 0) return []
    
    try {
      // 后端返回格式: {"result": ["{\"table1\": {...}, \"table2\": {...}}"]}
      const schemaString = rawSchema[0]
      const parsedSchema: ParsedSchema = JSON.parse(schemaString)
      
      return Object.entries(parsedSchema).map(([tableName, tableData]) => ({
        name: tableName,
        fields: Object.entries(tableData.fields).map(([fieldName, fieldInfo]) => ({
          name: fieldName,
          type: fieldInfo.type,
          nullable: fieldInfo.null === 'YES',
          isPrimary: fieldInfo.key === 'PRI',
          isIndex: fieldInfo.key !== '',
          default: fieldInfo.default
        }))
      }))
    } catch (error) {
      console.error('解析schema数据失败:', error)
      return []
    }
  }

  // 获取数据库结构
  const fetchSchema = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const rawSchema = await ApiClient.getSchema()
      const parsedTables = parseSchemaData(rawSchema)
      setTables(parsedTables)
      setSchema(rawSchema) // 保存原始数据到store
      
      // 获取每个表的记录数
      await fetchTableCounts(parsedTables)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '获取数据库结构失败'
      setError(errorMessage)
      console.error('获取schema失败:', err)
    } finally {
      setLoading(false)
    }
  }

  // 获取表记录数
  const fetchTableCounts = async (tableList: TableInfo[]) => {
    try {
      const updatedTables = await Promise.all(
        tableList.map(async (table) => {
          try {
            const result = await ApiClient.executeQuery(`SELECT COUNT(*) as count FROM \`${table.name}\``)
            const count = result.rows[0]?.count || 0
            return { ...table, recordCount: count }
          } catch (error) {
            console.warn(`获取表 ${table.name} 记录数失败:`, error)
            return { ...table, recordCount: 0 }
          }
        })
      )
      setTables(updatedTables)
    } catch (error) {
      console.warn('获取表记录数失败:', error)
    }
  }

  // 搜索过滤
  useEffect(() => {
    if (!searchTerm) {
      setFilteredTables(tables)
    } else {
      const filtered = tables.filter(table => 
        table.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        table.fields.some(field => 
          field.name.toLowerCase().includes(searchTerm.toLowerCase())
        )
      )
      setFilteredTables(filtered)
    }
  }, [tables, searchTerm])

  // 组件挂载时获取数据
  useEffect(() => {
    fetchSchema()
  }, [])

  // 切换表展开状态
  const toggleTable = (tableName: string) => {
    const newExpanded = new Set(expandedTables)
    if (newExpanded.has(tableName)) {
      newExpanded.delete(tableName)
    } else {
      newExpanded.add(tableName)
    }
    setExpandedTables(newExpanded)
  }

  // 获取字段类型颜色
  const getTypeColor = (type: string) => {
    const lowerType = type.toLowerCase()
    if (lowerType.includes('int') || lowerType.includes('bigint')) return 'text-blue-600'
    if (lowerType.includes('varchar') || lowerType.includes('text')) return 'text-green-600'
    if (lowerType.includes('decimal') || lowerType.includes('float')) return 'text-purple-600'
    if (lowerType.includes('date') || lowerType.includes('time')) return 'text-orange-600'
    return 'text-gray-600'
  }

  // 加载状态
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2 text-primary" />
          <p className="text-sm text-muted-foreground">加载数据库结构中...</p>
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
          <p className="text-xs text-muted-foreground mb-4">{error}</p>
          <Button onClick={fetchSchema} size="sm">
            重试
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 头部操作区 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-medium">数据库结构</h3>
          <span className="text-sm text-muted-foreground">
            ({filteredTables.length} 个表)
          </span>
        </div>
        <Button onClick={fetchSchema} size="sm" variant="outline">
          <RefreshCw className="h-4 w-4 mr-1" />
          刷新
        </Button>
      </div>

      {/* 搜索框 */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="搜索表名或字段名..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* 表列表 */}
      <div className="space-y-2 max-h-[calc(100vh-300px)] overflow-y-auto">
        {filteredTables.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            {searchTerm ? '未找到匹配的表或字段' : '暂无数据表'}
          </div>
        ) : (
          filteredTables.map((table) => (
            <Card key={table.name} className="overflow-hidden">
              <CardHeader 
                className="pb-2 cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => toggleTable(table.name)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {expandedTables.has(table.name) ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    <Table className="h-4 w-4 text-primary" />
                    <CardTitle className="text-base">{table.name}</CardTitle>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>{table.fields.length} 个字段</span>
                    {table.recordCount !== undefined && (
                      <span>{table.recordCount.toLocaleString()} 条记录</span>
                    )}
                  </div>
                </div>
              </CardHeader>
              
              {expandedTables.has(table.name) && (
                <CardContent className="pt-0">
                  <div className="space-y-1">
                    {table.fields.map((field) => (
                      <div 
                        key={field.name}
                        className="flex items-center justify-between py-2 px-3 rounded-md hover:bg-muted/30 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex items-center gap-1">
                            {field.isPrimary && (
                              <Key className="h-3 w-3 text-yellow-600" />
                            )}
                            {field.isIndex && !field.isPrimary && (
                              <div className="w-3 h-3 rounded-full bg-blue-500" />
                            )}
                          </div>
                          <span className="font-mono text-sm font-medium">
                            {field.name}
                          </span>
                        </div>
                        
                        <div className="flex items-center gap-4 text-sm">
                          <span className={`font-mono ${getTypeColor(field.type)}`}>
                            {field.type}
                          </span>
                          <span className="text-muted-foreground">
                            {field.nullable ? 'NULL' : 'NOT NULL'}
                          </span>
                          {field.default !== null && (
                            <span className="text-xs text-muted-foreground">
                              默认: {String(field.default)}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              )}
            </Card>
          ))
        )}
      </div>
    </div>
  )
} 