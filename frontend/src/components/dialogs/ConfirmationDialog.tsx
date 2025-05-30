"use client"

import React from 'react'
import { AlertTriangle, CheckCircle, Edit, Plus, Trash2, Layers } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { ConfirmationType } from '@/hooks/useConfirmation'

interface ConfirmationDialogProps {
  /** 对话框是否打开 */
  isOpen: boolean
  /** 操作类型 */
  type: ConfirmationType | null
  /** 对话框标题 */
  title: string
  /** 对话框描述 */
  description: string
  /** 要确认的内容 */
  content: string
  /** 是否是危险操作 */
  isDangerous?: boolean
  /** 是否正在加载 */
  isLoading?: boolean
  /** 确认回调 */
  onConfirm: () => void
  /** 取消回调 */
  onCancel: () => void
}

/**
 * 确认对话框组件
 * 
 * 功能：
 * - 显示操作预览和确认信息
 * - 根据操作类型显示不同的图标和样式
 * - 支持危险操作的特殊提示
 * - 提供确认和取消按钮
 * - 支持加载状态
 */
export function ConfirmationDialog({
  isOpen,
  type,
  title,
  description,
  content,
  isDangerous = false,
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmationDialogProps) {
  // 根据操作类型获取配置
  const getTypeConfig = (operationType: ConfirmationType | null) => {
    const configs = {
      modify: {
        icon: Edit,
        iconColor: 'text-blue-500',
        bgColor: 'bg-blue-50',
        confirmText: '确认修改',
        confirmVariant: 'default' as const,
      },
      add: {
        icon: Plus,
        iconColor: 'text-green-500',
        bgColor: 'bg-green-50',
        confirmText: '确认新增',
        confirmVariant: 'default' as const,
      },
      delete: {
        icon: Trash2,
        iconColor: 'text-red-500',
        bgColor: 'bg-red-50',
        confirmText: '确认删除',
        confirmVariant: 'destructive' as const,
      },
      composite: {
        icon: Layers,
        iconColor: 'text-purple-500',
        bgColor: 'bg-purple-50',
        confirmText: '确认执行',
        confirmVariant: 'default' as const,
      },
    }

    return operationType ? configs[operationType] : configs.modify
  }

  const config = getTypeConfig(type)
  const IconComponent = config.icon

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onCancel()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            {/* 操作类型图标 */}
            <div className={cn(
              "p-2 rounded-full",
              config.bgColor
            )}>
              <IconComponent className={cn("h-5 w-5", config.iconColor)} />
            </div>
            
            <div className="flex-1">
              <DialogTitle className="text-lg font-semibold">
                {title}
              </DialogTitle>
              <DialogDescription className="text-sm text-muted-foreground mt-1">
                {description}
              </DialogDescription>
            </div>

            {/* 危险操作警告图标 */}
            {isDangerous && (
              <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0" />
            )}
          </div>
        </DialogHeader>

        {/* 操作内容预览 */}
        <div className="my-4">
          <div className="border rounded-lg bg-muted/50 p-4 max-h-60 overflow-y-auto">
            <pre className="text-sm whitespace-pre-wrap font-mono text-muted-foreground">
              {content}
            </pre>
          </div>
          
          {/* 危险操作额外提示 */}
          {isDangerous && (
            <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-center gap-2 text-amber-800">
                <AlertTriangle className="h-4 w-4" />
                <span className="text-sm font-medium">
                  ⚠️ 危险操作提醒
                </span>
              </div>
              <p className="text-sm text-amber-700 mt-1">
                此操作不可撤销，请仔细确认操作内容后再继续。
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          {/* 取消按钮 */}
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1 sm:flex-none"
          >
            取消
          </Button>

          {/* 确认按钮 */}
          <Button
            variant={isDangerous ? 'destructive' : config.confirmVariant}
            onClick={onConfirm}
            disabled={isLoading}
            className="flex-1 sm:flex-none"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
                执行中...
              </>
            ) : (
              <>
                <CheckCircle className="h-4 w-4 mr-2" />
                {config.confirmText}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
} 