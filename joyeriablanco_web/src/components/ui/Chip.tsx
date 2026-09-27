import type { ReactNode } from 'react'
import { cx } from './cx'

export type ChipTone = 'success' | 'warning' | 'danger'

// DESIGN.md §Status Chips: fondo @ 8 %, borde @ 40 %, texto sólido; radio 0.
const tonos: Record<ChipTone, string> = {
  success: 'bg-success/8 border-success/40 text-success',
  warning: 'bg-warning/8 border-warning/40 text-warning',
  danger: 'bg-danger/8 border-danger/40 text-danger',
}

export function Chip({
  tone,
  children,
  className,
}: {
  tone: ChipTone
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={cx('inline-flex items-center border px-2 py-1 label-sm', tonos[tone], className)}
    >
      {children}
    </span>
  )
}
