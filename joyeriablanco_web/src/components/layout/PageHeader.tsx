import type { ReactNode } from 'react'

/** Título de página en Bodoni (headline-xl; headline-xl-mobile < 768 px) y subtítulo. */
export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
      <div className="flex flex-col gap-2">
        <h1 className="headline-xl-mobile text-on-surface md:headline-xl">{title}</h1>
        {subtitle ? <p className="body-lg text-on-surface-variant">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-col gap-3 sm:flex-row">{actions}</div> : null}
    </div>
  )
}
