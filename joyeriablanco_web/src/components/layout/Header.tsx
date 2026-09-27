import { Menu } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { UsuarioSalida } from '../../api/tipos'
import { claveDia, fechaLarga } from '../../lib/fechas'
import { Button } from '../ui/Button'
import { UserMenu } from './UserMenu'

function useFechaDeHoy(): Date {
  const [hoy, setHoy] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => {
      const ahora = new Date()
      setHoy((anterior) => (claveDia(anterior) === claveDia(ahora) ? anterior : ahora))
    }, 60_000)
    return () => {
      clearInterval(id)
    }
  }, [])
  return hoy
}

/** Cabecera: contexto, fecha larga en es-ES y menú de usuario. Sin campana (FR-039). */
export function Header({
  usuario,
  onAbrirMenu,
}: {
  usuario: UsuarioSalida
  onAbrirMenu: () => void
}) {
  const hoy = useFechaDeHoy()
  return (
    <header className="flex h-18 items-center justify-between gap-4 border-b border-primary-container/18 px-4 md:px-margin">
      <div className="flex items-center gap-3">
        <Button
          variant="icon"
          aria-label="Abrir menú de navegación"
          className="lg:hidden"
          onPress={onAbrirMenu}
        >
          <Menu aria-hidden="true" className="size-5" />
        </Button>
        <span className="body-lg text-on-surface-variant">Gestión de facturación</span>
      </div>
      <div className="flex items-center gap-5">
        <time dateTime={claveDia(hoy)} className="hidden body-md text-on-surface sm:block">
          {fechaLarga(hoy)}
        </time>
        <span aria-hidden="true" className="hidden h-8 w-px bg-outline-variant sm:block" />
        <UserMenu usuario={usuario} />
      </div>
    </header>
  )
}
