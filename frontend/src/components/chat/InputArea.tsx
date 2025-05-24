'use client'

import React, { useState } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Send } from 'lucide-react'
import { useConversationStore } from '@/store/conversationStore'

interface InputAreaProps {
  className?: string
}

export const InputArea = ({ className }: InputAreaProps) => {
  const { sendMessage, currentInput, updateInput, isTyping } = useConversationStore()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSend = async () => {
    if (!currentInput.trim() || isTyping || isSubmitting) return
    
    const messageContent = currentInput.trim()
    setIsSubmitting(true)
    
    try {
      await sendMessage(messageContent)
    } catch (error) {
      console.error('发送消息时出错:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isDisabled = isTyping || isSubmitting

  return (
    <div className={cn(
      "p-4 bg-background",
      className
    )}>
      <div className="flex gap-2 items-end">
        <Input
          value={currentInput}
          onChange={(e) => updateInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={
            isDisabled 
              ? "AI 正在思考中，请稍候..." 
              : "输入您的数据库操作需求（复杂查询可能需要1-2分钟）..."
          }
          disabled={isDisabled}
          className="flex-1"
        />
        <Button 
          onClick={handleSend}
          disabled={isDisabled || !currentInput.trim()}
          size="default"
          className="h-10 px-3"
          title={isDisabled ? "请等待当前请求完成" : "发送消息（Enter）"}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
} 