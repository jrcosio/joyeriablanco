import type { ReactNode } from 'react'
import { Button as AriaButton, type ButtonProps as AriaButtonProps } from 'react-aria-components'
import { cx } from './cx'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'icon'

const base =
  'inline-flex items-center justify-center gap-2 transition-colors duration-150 ' +
  'outline-none data-[focus-visible]:outline data-[focus-visible]:outline-1 ' +
  'data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-tertiary ' +
  'data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50 cursor-pointer select-none'

// DESIGN.md §Buttons (tokens por nombre)
const variantes: Record<ButtonVariant, string> = {
  primary:
    'h-11 px-6 label-lg bg-primary text-on-primary data-[hovered]:bg-tertiary ' +
    'data-[hovered]:shadow-aura data-[pressed]:bg-primary-container',
  secondary:
    'h-11 px-6 label-lg border border-primary-container text-on-surface bg-transparent ' +
    'data-[hovered]:bg-primary-container/8',
  ghost:
    'h-11 px-3 label-lg text-on-surface-variant border-b border-transparent ' +
    'data-[hovered]:text-on-surface',
  danger:
    'h-11 px-3 label-lg text-on-surface-variant border-b border-transparent ' +
    'data-[hovered]:text-danger data-[hovered]:border-danger data-[focus-visible]:text-danger',
  icon:
    'size-10 border border-outline-variant bg-surface-container-high text-primary ' +
    'data-[hovered]:border-primary-container data-[hovered]:bg-surface-container-highest',
}

export interface ButtonProps extends Omit<AriaButtonProps, 'className' | 'children'> {
  variant?: ButtonVariant
  className?: string
  children?: ReactNode
}

export function Button({ variant = 'primary', className, children, ...props }: ButtonProps) {
  return (
    <AriaButton {...props} className={cx(base, variantes[variant], className)}>
      {children}
    </AriaButton>
  )
}
