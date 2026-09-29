import { Link } from '@tanstack/react-router'
import { ClipboardList, FileText, Settings, Users, type LucideIcon } from 'lucide-react'
import type { Rol } from '../../api/tipos'
import { Chip } from '../ui/Chip'
import { Marca } from './Marca'

interface Entrada {
  etiqueta: string
  icono: LucideIcon
  to?: '/facturas' | '/clientes' | '/configuracion'
  soloAdmin?: boolean
}

// Presupuestos se muestra deshabilitada hasta su feature (FR-038 de 001; FR-041 de 002).
const ENTRADAS: readonly Entrada[] = [
  { etiqueta: 'Facturas', icono: FileText, to: '/facturas' },
  { etiqueta: 'Presupuestos', icono: ClipboardList },
  { etiqueta: 'Clientes', icono: Users, to: '/clientes' },
  { etiqueta: 'Configuración', icono: Settings, to: '/configuracion', soloAdmin: true },
]

const claseEntrada = 'flex h-12 items-center gap-3 px-4 title-md transition-colors'

export function Sidebar({ rol, onNavegar }: { rol: Rol; onNavegar?: () => void }) {
  return (
    <div className="flex h-full flex-col bg-surface-container-lowest">
      <div className="border-b border-primary-container/18 px-6 py-8">
        <Marca />
      </div>
      <nav aria-label="Navegación principal" className="flex-1 px-3 py-6">
        <ul className="flex flex-col gap-1">
          {ENTRADAS.filter((e) => !e.soloAdmin || rol === 'administrador').map((entrada) => {
            const Icono = entrada.icono
            if (!entrada.to) {
              return (
                <li key={entrada.etiqueta}>
                  <span
                    aria-disabled="true"
                    className={`${claseEntrada} cursor-not-allowed text-on-surface-variant/50`}
                  >
                    <Icono aria-hidden="true" className="size-5 shrink-0" />
                    <span className="min-w-0 flex-1 truncate">{entrada.etiqueta}</span>
                    <Chip tone="warning">Próximamente</Chip>
                  </span>
                </li>
              )
            }
            return (
              <li key={entrada.etiqueta}>
                <Link
                  to={entrada.to}
                  onClick={onNavegar}
                  className={`${claseEntrada} text-on-surface hover:bg-surface-container`}
                  activeProps={{
                    className:
                      'bg-surface-container-high text-primary hover:bg-surface-container-high',
                    'aria-current': 'page',
                  }}
                >
                  <Icono aria-hidden="true" className="size-5 shrink-0" />
                  <span>{entrada.etiqueta}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
    </div>
  )
}
