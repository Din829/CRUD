import React from 'react'
import { cn } from '@/lib/utils'

interface TypingIndicatorProps {
  isTyping: boolean
  className?: string
}

export function TypingIndicator({ isTyping, className }: TypingIndicatorProps) {
  if (!isTyping) return null
  
  return (
    <div className={cn(
      "flex justify-start w-full mb-4",
      className
    )}>
      <div className="bg-muted text-muted-foreground px-4 py-2 rounded-lg max-w-[80%]">
        <div className="flex items-center space-x-1">
          <span className="text-sm">AI 正在思考</span>
          <div className="flex space-x-1">
            <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce"></div>
            <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          </div>
        </div>
      </div>
    </div>
  )
} 