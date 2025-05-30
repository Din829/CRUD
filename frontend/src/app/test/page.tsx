import { ConfirmationDemo } from '@/components/demo/ConfirmationDemo'

/**
 * 测试页面
 * 
 * 用于测试阶段三的功能：
 * - 确认流程对话框
 * - 不同类型的操作确认
 * - 危险操作的特殊提示
 */
export default function TestPage() {
  return (
    <main className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">
            阶段三功能测试
          </h1>
          <p className="text-muted-foreground">
            确认流程对话框 & 操作预览功能
          </p>
        </div>
        
        <ConfirmationDemo />
        
        <div className="mt-8 text-center">
          <a 
            href="/"
            className="text-primary hover:underline"
          >
            ← 返回主页面
          </a>
        </div>
      </div>
    </main>
  )
} 