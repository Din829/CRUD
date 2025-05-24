'use client'

import React from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { MessageList } from './MessageList'
import { InputArea } from './InputArea'

interface ChatInterfaceProps {
  className?: string
}

export function ChatInterface({ className }: ChatInterfaceProps) {
  return (
    <Card className={cn("flex flex-col h-full", className)}>
      <CardHeader className="flex-shrink-0 pb-3">
        <CardTitle className="text-lg">对话区域</CardTitle>
      </CardHeader>
      
      <CardContent className="flex-1 min-h-0 flex flex-col p-0">
        {/* 消息列表区域 - 可滚动 */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <MessageList />
        </div>
        
        {/* 输入区域 - 固定在底部 */}
        <div className="flex-shrink-0 border-t bg-background">
          <InputArea />
        </div>
      </CardContent>
    </Card>
  )
} 