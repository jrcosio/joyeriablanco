import logo from '../../assets/brand/logo.png'
import { cx } from '../ui/cx'

/** Logo circular + "JOYERÍA BLANCO" con filete dorado (FR-038, FR-042). */
export function Marca({ tamano = 'md', className }: { tamano?: 'md' | 'lg'; className?: string }) {
  const lado = tamano === 'lg' ? 'size-32' : 'size-28'
  return (
    <div className={cx('flex flex-col items-center gap-4', className)}>
      <img
        src={logo}
        alt="Joyería Blanco"
        width={128}
        height={128}
        className={cx(lado, 'select-none')}
      />
      <span className="font-display text-[1.05rem] font-medium tracking-[0.28em] text-on-surface uppercase">
        Joyería Blanco
      </span>
      <span aria-hidden="true" className="h-px w-10 bg-primary" />
    </div>
  )
}
