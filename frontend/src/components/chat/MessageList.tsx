'use client'

import React, { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'
import { useConversationStore } from '@/store/conversationStore'

interface MessageListProps {
  className?: string
}

export function MessageList({ className }: MessageListProps) {
  const { messages, isTyping } = useConversationStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  
  // 自动滚动到底部
  const scrollToBottom = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: 'smooth'
      })
    }
  }
  
  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])
  
  return (
    <div 
      ref={scrollContainerRef}
      className={cn(
        "h-full overflow-y-auto overflow-x-hidden p-4 space-y-2",
        // 自定义滚动条样式
        "scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent",
        className
      )}
    >
      {/* 空状态 */}
      {messages.length === 0 && (
        <div className="flex items-center justify-center min-h-full">
          <div className="text-center text-muted-foreground">
            <p className="text-lg mb-2">🤖 您好！我是 DifyLang 智能助手</p>
            <p className="text-sm">请输入您的数据库操作需求，我来帮您处理</p>
          </div>
        </div>
      )}
      
      {/* 消息列表 */}
      <div className="space-y-2">
        {messages.map(message => (
          <MessageBubble 
            key={message.id} 
            message={message}
          />
        ))}
        
        {/* 打字指示器 */}
        <TypingIndicator isTyping={isTyping} />
      </div>
      
      {/* 滚动锚点 */}
      <div ref={messagesEndRef} className="h-1" />
    </div>
  )
} 