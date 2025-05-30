"use client"

import React from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useConfirmation } from '@/hooks/useConfirmation'
import { ConfirmationDialog } from '@/components/dialogs/ConfirmationDialog'

/**
 * 确认流程演示组件
 * 
 * 用于测试和展示阶段三的确认功能：
 * - 不同类型的操作确认
 * - 确认对话框的交互
 * - 危险操作的特殊提示
 */
export function ConfirmationDemo() {
  const confirmation = useConfirmation()

  const handleTestConfirm = () => {
    console.log('✅ 用户确认了操作')
    alert('操作已确认！')
  }

  const handleTestCancel = () => {
    console.log('❌ 用户取消了操作')
    alert('操作已取消！')
  }

  const demoOperations = [
    {
      type: 'modify' as const,
      title: '测试修改操作',
      content: `{
  "table_name": "users",
  "primary_key": "id",
  "primary_value": 1,
  "update_fields": {
    "name": "张三",
    "email": "zhangsan@example.com",
    "status": "active"
  }
}`,
      description: '模拟修改用户信息的确认流程',
    },
    {
      type: 'add' as const,
      title: '测试新增操作',
      content: `{
  "table_name": "products",
  "fields": {
    "name": "iPhone 15",
    "price": 7999,
    "category": "电子产品",
    "stock": 100
  }
}`,
      description: '模拟新增产品的确认流程',
    },
    {
      type: 'delete' as const,
      title: '测试删除操作',
      content: `即将删除以下记录：

表名: orders
条件: status = 'cancelled' AND created_at < '2024-01-01'
预计影响行数: 156 条记录

警告：此操作不可撤销！`,
      description: '模拟删除订单的确认流程（危险操作）',
    },
    {
      type: 'composite' as const,
      title: '测试复合操作',
      content: `批量操作计划：

1. 更新用户状态 (users表, 5条记录)
2. 新增订单记录 (orders表, 3条记录)  
3. 更新库存数量 (products表, 8条记录)

总计：16个操作将被执行`,
      description: '模拟批量复合操作的确认流程',
    },
  ]

  return (
    <>
      <Card className="w-full max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle className="text-xl">🧪 确认流程测试</CardTitle>
          <CardDescription>
            阶段三功能演示：测试不同类型的操作确认对话框
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {demoOperations.map((operation, index) => (
            <div key={index} className="p-4 border rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium">{operation.title}</h3>
                <Button
                  size="sm"
                  variant={operation.type === 'delete' ? 'destructive' : 'default'}
                  onClick={() => confirmation.showConfirmation({
                    type: operation.type,
                    content: operation.content,
                    onConfirm: handleTestConfirm,
                    onCancel: handleTestCancel,
                  })}
                >
                  触发确认
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                {operation.description}
              </p>
            </div>
          ))}
          
          {/* 快捷测试按钮 */}
          <div className="pt-4 border-t">
            <h4 className="font-medium mb-3">快捷测试方法：</h4>
            <div className="grid grid-cols-2 gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => confirmation.confirmModify(
                  '修改用户 ID=123 的邮箱地址为 new@example.com',
                  handleTestConfirm
                )}
              >
                快速修改测试
              </Button>
              
              <Button
                size="sm"
                variant="outline"
                onClick={() => confirmation.confirmAdd(
                  '新增产品: MacBook Pro M3, 价格: ¥16999',
                  handleTestConfirm
                )}
              >
                快速新增测试
              </Button>
              
              <Button
                size="sm"
                variant="destructive"
                onClick={() => confirmation.confirmDelete(
                  '删除订单 #12345 (包含 3 个商品)',
                  handleTestConfirm
                )}
              >
                快速删除测试
              </Button>
              
              <Button
                size="sm"
                variant="outline"
                onClick={() => confirmation.confirmComposite(
                  '执行 8 个批量操作：4个更新 + 2个新增 + 2个删除',
                  handleTestConfirm
                )}
              >
                快速复合测试
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 确认对话框 */}
      <ConfirmationDialog
        isOpen={confirmation.isOpen}
        type={confirmation.type}
        title={confirmation.title}
        description={confirmation.description}
        content={confirmation.content}
        isDangerous={confirmation.isDangerous}
        isLoading={confirmation.isLoading}
        onConfirm={confirmation.handleConfirm}
        onCancel={confirmation.handleCancel}
      />
    </>
  )
} 