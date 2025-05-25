'use client'

import React, { useState, KeyboardEvent } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Send, TestTube } from 'lucide-react'
import { useConversationStore } from '@/store/conversationStore'

interface InputAreaProps {
  className?: string
}

export const InputArea = ({ className }: InputAreaProps) => {
  const { currentInput, isTyping, sendMessage, updateInput, addMessage } = useConversationStore()
  const [input, setInput] = useState('')
  
  const handleSend = async () => {
    const message = input.trim() || currentInput.trim()
    if (message && !isTyping) {
      setInput('')
      updateInput('')
      await sendMessage(message)
    }
  }
  
  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }
  
  const handleInputChange = (value: string) => {
    setInput(value)
    updateInput(value)
  }
  
  // 测试函数：生成多条消息测试滚动
  const generateTestMessages = () => {
    const testMessages = [
      { content: '这是第一条测试消息', role: 'user' as const },
      { content: '收到您的消息，正在处理中...', role: 'assistant' as const },
      { content: '查询用户信息', role: 'user' as const },
      { content: '已为您查询到以下用户信息：\n用户1: 张三\n用户2: 李四\n用户3: 王五', role: 'assistant' as const },
      { content: '分析一下数据库性能', role: 'user' as const },
      { content: '数据库性能分析结果：\n- 查询响应时间：平均 150ms\n- 连接池使用率：60%\n- 慢查询数量：3个\n建议优化索引以提升性能。', role: 'assistant' as const },
      { content: '请帮我创建新用户', role: 'user' as const },
      { content: '好的，我来帮您创建新用户。请提供以下信息：\n1. 用户名\n2. 邮箱地址\n3. 初始密码\n4. 用户角色', role: 'assistant' as const },
      { content: '用户名：test_user，邮箱：test@example.com，密码：123456，角色：普通用户', role: 'user' as const },
      { content: '✅ 新用户创建成功！\n\n用户详情：\n- ID: 106\n- 用户名: test_user\n- 邮箱: test@example.com\n- 角色: 普通用户\n- 创建时间: 2025-01-31 15:30:00\n\n用户已添加到系统中。', role: 'assistant' as const }
    ]
    
    testMessages.forEach((msg, index) => {
      setTimeout(() => {
        addMessage(msg)
      }, index * 500) // 每500ms添加一条消息
    })
  }
  
  return (
    <div className={cn(
      "p-4 bg-background space-y-3",
      className
    )}>
      {/* 测试按钮 */}
      <div className="flex justify-center">
        <Button
          variant="outline"
          size="sm"
          onClick={generateTestMessages}
          disabled={isTyping}
          className="text-xs"
        >
          <TestTube className="w-3 h-3 mr-1" />
          测试滚动
        </Button>
      </div>
      
      {/* 输入区域 */}
      <div className="flex gap-2 items-end">
        <Input
          value={input}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={isTyping ? "AI 正在思考中，请稍候..." : "输入您的数据库操作需求（复杂查询可能需要1-2分钟）..."}
          disabled={isTyping}
          className="flex-1"
        />
        <Button 
          onClick={handleSend}
          disabled={isTyping || (!input.trim() && !currentInput.trim())}
          size="default"
          className="h-10 px-3"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
      
      {/* 状态提示 */}
      {isTyping && (
        <p className="text-xs text-muted-foreground text-center">
          ⏳ 正在处理您的请求，复杂查询可能需要较长时间...
        </p>
      )}
    </div>
  )
} 