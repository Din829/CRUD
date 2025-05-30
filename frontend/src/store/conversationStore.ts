import { create } from 'zustand'
import type { Message } from '@/types'
import { ApiClient } from '@/lib/api'

interface ConversationState {
  // 状态
  messages: Message[]
  isTyping: boolean
  currentInput: string
  conversationId: string
  
  // 动作
  sendMessage: (content: string) => Promise<void>
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void
  clearConversation: () => void
  setTyping: (typing: boolean) => void
  updateInput: (input: string) => void
  setConversationId: (id: string) => void
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  // 初始状态 - 立即生成一个session ID
  messages: [],
  isTyping: false,
  currentInput: '',
  conversationId: `session_${Date.now()}`,
  
  // 动作实现
  sendMessage: async (content: string) => {
    const { messages, addMessage, conversationId } = get()
    
    // 添加用户消息
    addMessage({
      content,
      role: 'user'
    })
    
    // 清空输入
    set({ currentInput: '' })
    
    // 设置 AI 思考状态
    set({ isTyping: true })
    
    try {
      // 调用 LangGraph API - 始终传递有效的conversationId
      console.log('发送消息到 LangGraph:', content, '会话ID:', conversationId)
      const response = await ApiClient.sendMessage(content, conversationId)
      
      // 更新会话 ID（如果后端返回了新的session_id）
      if (response.session_id && response.session_id !== conversationId) {
        console.log('更新会话ID:', response.session_id)
        set({ conversationId: response.session_id })
      }
      
      // 添加 AI 回复
      addMessage({
        content: response.message,
        role: 'assistant'
      })
      
      // 如果有错误，也添加错误信息
      if (!response.success && response.error) {
        console.error('LangGraph 返回错误:', response.error)
      }
      
    } catch (error: any) {
      console.error('发送消息失败:', error)
      
      let errorMessage = '抱歉，处理您的请求时出现问题，请稍后再试。'
      
      // 根据错误类型提供更友好的提示
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        errorMessage = '⏰ 请求处理时间较长，服务器可能正在处理复杂查询，请稍后再试或尝试简化您的问题。'
      } else if (error.response?.status === 500) {
        errorMessage = '🔧 服务器内部错误，请检查您的输入是否正确，或联系管理员。'
      } else if (error.response?.status === 404) {
        errorMessage = '🔍 服务接口未找到，请确认后端服务正在运行。'
      } else if (error.response?.status >= 400 && error.response?.status < 500) {
        errorMessage = `❌ 请求错误 (${error.response.status})：${error.response.data?.message || '请检查输入格式'}`
      } else if (!navigator.onLine) {
        errorMessage = '🌐 网络连接异常，请检查网络连接后重试。'
      }
      
      // 添加错误消息
      addMessage({
        content: errorMessage,
        role: 'assistant'
      })
    } finally {
      // 取消 AI 思考状态
      set({ isTyping: false })
    }
  },
  
  addMessage: (message) => {
    const newMessage: Message = {
      ...message,
      id: Date.now().toString(),
      timestamp: new Date()
    }
    
    set(state => ({
      messages: [...state.messages, newMessage]
    }))
  },
  
  clearConversation: () => {
    set({
      messages: [],
      isTyping: false,
      currentInput: '',
      conversationId: `session_${Date.now()}`  // 重新生成新的session ID
    })
  },
  
  setTyping: (typing: boolean) => {
    set({ isTyping: typing })
  },
  
  updateInput: (input: string) => {
    set({ currentInput: input })
  },
  
  setConversationId: (id: string) => {
    set({ conversationId: id })
  }
})) 