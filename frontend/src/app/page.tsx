import { ChatInterface } from '@/components/chat/ChatInterface'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function Home() {
  return (
    <main className="h-screen flex flex-col bg-background">
      {/* 页面头部 */}
      <div className="flex-shrink-0 text-center py-6">
        <h1 className="text-4xl font-bold text-foreground mb-2">
          DifyLang
        </h1>
        <p className="text-xl text-muted-foreground">
          智能数据库操作平台
        </p>
      </div>
      
      {/* 主内容区域 */}
      <div className="flex-1 min-h-0 px-4 pb-6">
        <div className="max-w-6xl mx-auto h-full">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
            {/* 聊天区域 */}
            <ChatInterface />
            
            {/* 数据展示区域 */}
            <Card className="flex flex-col">
              <CardHeader className="flex-shrink-0">
                <CardTitle className="text-lg">数据展示</CardTitle>
              </CardHeader>
              <CardContent className="flex-1 min-h-0 flex items-center justify-center">
                <p className="text-muted-foreground">查询结果将在这里显示...</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </main>
  )
} 