'use client'

import React, { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'
import { useConversationStore } from '@/store/conversationStore'
import { useDataStore } from '@/store'
import { extractTableDataFromMessage, createQueryResult, hasQueryResult } from '@/lib/dataParser'

interface MessageListProps {
  className?: string
}

export function MessageList({ className }: MessageListProps) {
  const { messages, isTyping } = useConversationStore()
  const { setQueryResult, setTableData } = useDataStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  
  // 自动滚动到底部
  const scrollToBottom = () => {
    if (scrollContainerRef.current) {
      const container = scrollContainerRef.current
      // 直接设置scrollTop到最大值
      container.scrollTop = container.scrollHeight
    }
  }
  
  // 当消息或打字状态变化时滚动到底部
  useEffect(() => {
    // 使用requestAnimationFrame确保DOM更新后再滚动
    const timer = requestAnimationFrame(() => {
      setTimeout(() => {
        scrollToBottom()
      }, 50)
    })
    
    return () => cancelAnimationFrame(timer)
  }, [messages, isTyping])
  
  // 监听新消息，解析查询结果
  useEffect(() => {
    if (messages.length === 0) return
    
    const lastMessage = messages[messages.length - 1]
    
    // 只处理AI助手的消息
    if (lastMessage.role === 'assistant') {
      const content = lastMessage.content
      
      // 检查是否包含查询结果
      if (hasQueryResult(content)) {
        const tableData = extractTableDataFromMessage(content)
        
        if (tableData && tableData.length > 0) {
          // 更新数据store
          setTableData(tableData)
          const queryResult = createQueryResult(tableData)
          setQueryResult(queryResult)
        }
      }
    }
  }, [messages, setQueryResult, setTableData])
  
  return (
    <div 
      ref={scrollContainerRef}
      className={cn(
        "h-full w-full overflow-y-auto overflow-x-hidden",
        // 自定义滚动条样式
        "scrollbar-thin",
        className
      )}
      style={{ maxHeight: '100%' }}
    >
      {/* 空状态 */}
      {messages.length === 0 && !isTyping && (
        <div className="flex items-center justify-center h-full p-4">
          <div className="text-center text-muted-foreground">
            <p className="text-lg mb-2">🤖 您好！我是 DifyLang 智能助手</p>
            <p className="text-sm">请输入您的数据库操作需求，我来帮您处理</p>
          </div>
        </div>
      )}
      
      {/* 消息内容区域 - 使用简单的div，不用flex */}
      {(messages.length > 0 || isTyping) && (
        <div className="p-4 space-y-3">
          {/* 消息列表 */}
          {messages.map(message => (
            <MessageBubble 
              key={message.id} 
              message={message}
            />
          ))}
          
          {/* 打字指示器 */}
          {isTyping && <TypingIndicator isTyping={isTyping} />}
          
          {/* 滚动锚点 */}
          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  )
} 