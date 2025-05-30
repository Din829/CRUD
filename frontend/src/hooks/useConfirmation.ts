"use client"

import { useState, useCallback } from 'react'

/**
 * 确认对话框类型
 */
export type ConfirmationType = 'modify' | 'add' | 'delete' | 'composite'

/**
 * 确认对话框状态接口
 */
interface ConfirmationState {
  isOpen: boolean
  type: ConfirmationType | null
  title: string
  description: string
  content: string
  onConfirm: (() => void) | null
  onCancel: (() => void) | null
  isLoading: boolean
  isDangerous: boolean
}

/**
 * 确认流程Hook
 * 
 * 用途：
 * - 管理确认对话框的显示/隐藏状态
 * - 处理不同类型的操作确认（修改、新增、删除、复合）
 * - 提供确认和取消回调
 * - 支持危险操作的特殊样式
 */
export function useConfirmation() {
  const [state, setState] = useState<ConfirmationState>({
    isOpen: false,
    type: null,
    title: '',
    description: '',
    content: '',
    onConfirm: null,
    onCancel: null,
    isLoading: false,
    isDangerous: false,
  })

  /**
   * 显示确认对话框
   */
  const showConfirmation = useCallback((options: {
    type: ConfirmationType
    title?: string
    description?: string
    content: string
    onConfirm: () => void
    onCancel?: () => void
    isDangerous?: boolean
  }) => {
    const typeConfig = {
      modify: { title: '确认修改', description: '请确认以下修改信息' },
      add: { title: '确认新增', description: '请确认以下新增信息' },
      delete: { title: '确认删除', description: '此操作不可撤销，请仔细确认' },
      composite: { title: '确认复合操作', description: '请确认以下批量操作' },
    }

    setState({
      isOpen: true,
      type: options.type,
      title: options.title || typeConfig[options.type].title,
      description: options.description || typeConfig[options.type].description,
      content: options.content,
      onConfirm: options.onConfirm,
      onCancel: options.onCancel || null,
      isLoading: false,
      isDangerous: options.isDangerous || options.type === 'delete',
    })
  }, [])

  /**
   * 隐藏确认对话框
   */
  const hideConfirmation = useCallback(() => {
    setState(prev => ({
      ...prev,
      isOpen: false,
    }))
  }, [])

  /**
   * 处理确认操作
   */
  const handleConfirm = useCallback(async () => {
    if (!state.onConfirm) return

    setState(prev => ({ ...prev, isLoading: true }))

    try {
      await state.onConfirm()
      hideConfirmation()
    } catch (error) {
      console.error('确认操作失败:', error)
      // 不关闭对话框，让用户看到错误状态
    } finally {
      setState(prev => ({ ...prev, isLoading: false }))
    }
  }, [state.onConfirm, hideConfirmation])

  /**
   * 处理取消操作
   */
  const handleCancel = useCallback(() => {
    if (state.onCancel) {
      state.onCancel()
    }
    hideConfirmation()
  }, [state.onCancel, hideConfirmation])

  /**
   * 预设的确认操作快捷方法
   */
  const confirmModify = useCallback((content: string, onConfirm: () => void) => {
    showConfirmation({
      type: 'modify',
      content,
      onConfirm,
    })
  }, [showConfirmation])

  const confirmAdd = useCallback((content: string, onConfirm: () => void) => {
    showConfirmation({
      type: 'add',
      content,
      onConfirm,
    })
  }, [showConfirmation])

  const confirmDelete = useCallback((content: string, onConfirm: () => void) => {
    showConfirmation({
      type: 'delete',
      content,
      onConfirm,
      isDangerous: true,
    })
  }, [showConfirmation])

  const confirmComposite = useCallback((content: string, onConfirm: () => void) => {
    showConfirmation({
      type: 'composite',
      content,
      onConfirm,
    })
  }, [showConfirmation])

  return {
    // 状态
    isOpen: state.isOpen,
    type: state.type,
    title: state.title,
    description: state.description,
    content: state.content,
    isLoading: state.isLoading,
    isDangerous: state.isDangerous,

    // 操作方法
    showConfirmation,
    hideConfirmation,
    handleConfirm,
    handleCancel,

    // 快捷方法
    confirmModify,
    confirmAdd,
    confirmDelete,
    confirmComposite,
  }
} 