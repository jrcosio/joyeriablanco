import { Link } from '@tanstack/react-router'
import { ClipboardList, FileText, Settings, Users, type LucideIcon } from 'lucide-react'
import type { Rol } from '../../api/tipos'
import { Marca } from './Marca'

interface Entrada {
  etiqueta: string
  icono: LucideIcon
  to: '/facturas' | '/presupuestos' | '/clientes' | '/configuracion'
  soloAdmin?: boolean
}

// Presupuestos, activa desde la feature 005 (FR-032).
const ENTRADAS: readonly Entrada[] = [
  { etiqueta: 'Facturas', icono: FileText, to: '/facturas' },
  { etiqueta: 'Presupuestos', icono: ClipboardList, to: '/presupuestos' },
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
