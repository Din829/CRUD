'use client'

import { useState } from 'react'
import { ChatInterface } from '@/components/chat/ChatInterface'
import { SchemaView } from '@/components/data/SchemaView'
import { DataViewer } from '@/components/data/DataViewer'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { TestTube, ChevronUp, ChevronDown } from 'lucide-react'

export default function Home() {
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [isSchemaCollapsed, setIsSchemaCollapsed] = useState(false)

  // 处理表选择
  const handleTableSelect = (tableName: string) => {
    setSelectedTable(tableName)
  }

  // 切换数据库结构折叠状态
  const toggleSchemaCollapse = () => {
    setIsSchemaCollapsed(!isSchemaCollapsed)
  }
  return (
    <main className="h-screen flex flex-col bg-background">
      {/* 页面头部 - 增加测试入口 */}
      <div className="flex-shrink-0 text-center py-3 border-b">
        <div className="flex items-center justify-between max-w-6xl mx-auto px-4">
          <div className="flex-1"></div>
          
          <div className="text-center">
            <h1 className="text-2xl font-bold text-foreground mb-1">
              DifyLang
            </h1>
            <p className="text-sm text-muted-foreground">
              智能数据库操作平台
            </p>
          </div>
          
          <div className="flex-1 flex justify-end">
            <a href="/test">
              <Button 
                variant="outline" 
                size="sm"
                className="flex items-center gap-2"
              >
                <TestTube className="h-4 w-4" />
                阶段三测试
              </Button>
            </a>
          </div>
        </div>
      </div>
      
      {/* 主内容区域 - 一半一半布局 */}
      <div className="flex-1 min-h-0 flex">
        {/* 聊天区域 - 占据一半空间 */}
        <div className="w-1/2 min-h-0 p-4">
          <ChatInterface />
        </div>
        
        {/* 数据展示区域 - 占据一半空间 */}
        <div className="w-1/2 min-h-0 border-l p-4 flex flex-col gap-4">
          {/* 数据库结构区域 - 可折叠 */}
          <Card className={`flex flex-col transition-all duration-300 ${
            isSchemaCollapsed ? 'h-16' : 'h-80'
          }`}>
            <CardHeader 
              className="flex-shrink-0 pb-2 cursor-pointer hover:bg-muted/50 transition-colors"
              onClick={toggleSchemaCollapse}
            >
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">数据库结构</CardTitle>
                <Button variant="ghost" size="sm">
                  {isSchemaCollapsed ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronUp className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </CardHeader>
            {!isSchemaCollapsed && (
              <CardContent className="flex-1 min-h-0 overflow-hidden p-4">
                <div className="h-full overflow-auto">
                  <SchemaView 
                    selectedTable={selectedTable}
                    onTableSelect={handleTableSelect}
                  />
                </div>
              </CardContent>
            )}
          </Card>

          {/* 表数据查看区域 - 主要展示区域 */}
          <div className="flex-1 min-h-0">
            <DataViewer selectedTable={selectedTable} />
          </div>
        </div>
      </div>
    </main>
  )
} 