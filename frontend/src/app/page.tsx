export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-4">
            DifyLang
          </h1>
          <p className="text-xl text-muted-foreground">
            智能数据库操作平台
          </p>
        </div>
        
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 聊天区域 */}
            <div className="bg-card border border-border rounded-lg p-6">
              <h2 className="text-2xl font-semibold mb-4">对话区域</h2>
              <div className="h-96 bg-muted rounded-md p-4 mb-4">
                <p className="text-muted-foreground">聊天消息将在这里显示...</p>
              </div>
              <div className="flex gap-2">
                <input 
                  type="text" 
                  placeholder="输入您的数据库操作需求..."
                  className="flex-1 px-3 py-2 border border-input rounded-md bg-background"
                />
                <button className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
                  发送
                </button>
              </div>
            </div>
            
            {/* 数据展示区域 */}
            <div className="bg-card border border-border rounded-lg p-6">
              <h2 className="text-2xl font-semibold mb-4">数据展示</h2>
              <div className="h-96 bg-muted rounded-md p-4">
                <p className="text-muted-foreground">查询结果将在这里显示...</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
} 