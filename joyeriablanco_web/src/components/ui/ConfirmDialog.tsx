import type { ReactNode } from 'react'
import { Button } from './Button'
import { Dialog } from './Dialog'

export interface ConfirmDialogProps {
  title: string
  isOpen: boolean
  onOpenChange: (abierto: boolean) => void
  onConfirm: () => void
  confirmLabel: string
  children: ReactNode
  destructive?: boolean
  isPending?: boolean
}

/** Diálogo de confirmación de nivel 2 (FR-058). */
export function ConfirmDialog({
  title,
  isOpen,
  onOpenChange,
  onConfirm,
  confirmLabel,
  children,
  destructive = false,
  isPending = false,
}: ConfirmDialogProps) {
  return (
    <Dialog title={title} role="alertdialog" isOpen={isOpen} onOpenChange={onOpenChange}>
      <div className="body-md text-on-surface-variant">{children}</div>
      <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button
          variant="secondary"
          onPress={() => {
            onOpenChange(false)
          }}
        >
          Cancelar
        </Button>
        <Button
          variant={destructive ? 'danger' : 'primary'}
          isDisabled={isPending}
          onPress={onConfirm}
        >
          {confirmLabel}
        </Button>
      </div>
    </Dialog>
  )
}
