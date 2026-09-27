import type { HTMLAttributes } from 'react'
import { cx } from './cx'

/** Tarjeta de nivel 1: surface-container con filete de 1 px en primary-container @ 18 %. */
export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...props}
      className={cx('border border-primary-container/18 bg-surface-container', className)}
    />
  )
}
