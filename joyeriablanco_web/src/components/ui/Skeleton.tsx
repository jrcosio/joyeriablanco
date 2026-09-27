import { cx } from './cx'

/** Marcador de carga con la geometría final (FR-057). */
export function Skeleton({ className }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cx('block animate-pulse bg-surface-container-high', className)}
    />
  )
}
