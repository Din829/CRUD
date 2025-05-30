"use client"

import React, { useState } from 'react'
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useConversationStore } from '@/store/conversationStore'
import type { Message } from '@/types'

interface MessageBubbleProps {
  message: Message
  className?: string
}

/**
 * 消息气泡组件
 * 
 * 修复后的确认流程逻辑：
 * - 识别后端发送的确认消息（包含"请确认，并回复'是'/'否'"）
 * - 显示确认和取消按钮
 * - 直接发送"是"/"否"给后端，不再弹出额外的确认对话框
 * - 避免重复循环
 */
export function MessageBubble({ message, className }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const { sendMessage } = useConversationStore()
  const [isProcessing, setIsProcessing] = useState(false)

  /**
   * 检测是否为后端发送的确认类消息
   * 更精确的匹配，避免误识别
   */
  const isConfirmationMessage = !isUser && (
    // 后端确认消息的标准格式
    (message.content.includes('请确认，并回复') && message.content.includes('是') && message.content.includes('否')) ||
    (message.content.includes('以下是即将') && message.content.includes('请确认') && message.content.includes('回复')) ||
    // 删除确认的特殊格式
    (message.content.includes('请仔细检查以下将要删除的内容') && message.content.includes('请输入')) ||
    // 其他后端确认消息格式
    (message.content.includes('即将【') && message.content.includes('】的信息') && message.content.includes('请确认'))
  )

  /**
   * 检测确认消息的操作类型
   */
  const getConfirmationType = (): 'modify' | 'add' | 'delete' | 'composite' => {
    const content = message.content.toLowerCase()
    if (content.includes('删除') || content.includes('delete')) return 'delete'
    if (content.includes('修改') || content.includes('modify') || content.includes('更新')) return 'modify'
    if (content.includes('新增') || content.includes('添加') || content.includes('add')) return 'add'
    if (content.includes('复合') || content.includes('批量') || content.includes('composite')) return 'composite'
    return 'modify' // 默认
  }

  /**
   * 处理确认操作 - 直接发送"是"给后端
   */
  const handleConfirm = async () => {
    setIsProcessing(true)
    try {
      await sendMessage('是')
    } catch (error) {
      console.error('发送确认消息失败:', error)
    } finally {
      setIsProcessing(false)
    }
  }

  /**
   * 处理取消操作 - 直接发送"否"给后端
   */
  const handleCancel = async () => {
    setIsProcessing(true)
    try {
      await sendMessage('否')
    } catch (error) {
      console.error('发送取消消息失败:', error)
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <div className={cn(
      "flex w-full mb-4",
      isUser ? "justify-end" : "justify-start",
      className
    )}>
      <div className={cn(
        "max-w-[80%] px-4 py-2 rounded-lg text-sm",
        isUser 
          ? "bg-primary text-primary-foreground ml-auto" 
          : "bg-muted text-muted-foreground mr-auto"
      )}>
        {/* 消息内容 */}
        <div className="whitespace-pre-wrap">
          {message.content}
        </div>
        
        {/* 确认消息的操作按钮 */}
        {isConfirmationMessage && (
          <div className="mt-3 pt-3 border-t border-border/50">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={handleConfirm}
                disabled={isProcessing}
                className="flex-1 h-8"
                variant={getConfirmationType() === 'delete' ? 'destructive' : 'default'}
              >
                {isProcessing ? (
                  <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-current mr-1" />
                ) : (
                  <CheckCircle className="h-3 w-3 mr-1" />
                )}
                是
              </Button>
              
              <Button
                size="sm"
                variant="outline"
                onClick={handleCancel}
                disabled={isProcessing}
                className="flex-1 h-8"
              >
                <XCircle className="h-3 w-3 mr-1" />
                否
              </Button>
            </div>
            
            {/* 危险操作提示 */}
            {getConfirmationType() === 'delete' && (
              <div className="mt-2 flex items-center gap-1 text-xs text-amber-600">
                <AlertTriangle className="h-3 w-3" />
                <span>此操作不可撤销，请谨慎确认</span>
              </div>
            )}
          </div>
        )}
        
        {/* 时间戳 */}
        <div className={cn(
          "text-xs mt-1 opacity-70",
          isUser ? "text-right" : "text-left"
        )}>
          {message.timestamp.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>
      </div>
    </div>
  )
} 