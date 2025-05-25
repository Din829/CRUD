import { ChatInterface } from '@/components/chat/ChatInterface'
import { SchemaView } from '@/components/data/SchemaView'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function Home() {
  return (
    <main className="h-screen flex flex-col bg-background">
      {/* 页面头部 - 缩小高度 */}
      <div className="flex-shrink-0 text-center py-3 border-b">
        <h1 className="text-2xl font-bold text-foreground mb-1">
          DifyLang
        </h1>
        <p className="text-sm text-muted-foreground">
          智能数据库操作平台
        </p>
      </div>
      
      {/* 主内容区域 - 一半一半布局 */}
      <div className="flex-1 min-h-0 flex">
        {/* 聊天区域 - 占据一半空间 */}
        <div className="w-1/2 min-h-0 p-4">
          <ChatInterface />
        </div>
        
        {/* 数据展示区域 - 占据一半空间 */}
        <div className="w-1/2 min-h-0 border-l p-4">
          <Card className="h-full flex flex-col">
            <CardHeader className="flex-shrink-0 pb-3">
              <CardTitle className="text-lg">数据库结构</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 min-h-0 overflow-hidden p-4">
              <div className="h-full overflow-auto">
                <SchemaView />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  )
} 