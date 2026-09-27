import type { ReactNode } from 'react'

export interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-16 text-center">
      {icon ? (
        <span aria-hidden="true" className="text-primary-container">
          {icon}
        </span>
      ) : null}
      <p className="headline-sm text-on-surface">{title}</p>
      {description ? (
        <p className="max-w-md body-md text-on-surface-variant">{description}</p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  )
}
