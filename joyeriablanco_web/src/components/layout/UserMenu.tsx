import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { ChevronDown, LogOut, UserRound } from 'lucide-react'
import { Button, Menu, MenuItem, MenuTrigger, Popover, Separator } from 'react-aria-components'
import type { UsuarioSalida } from '../../api/tipos'
import { cerrarSesion } from '../../auth/session'
import { iniciales } from '../../lib/texto'

const ROLES = { administrador: 'Administrador', empleado: 'Empleado' } as const

const claseItem =
  'flex cursor-pointer items-center gap-3 px-4 py-3 body-md text-on-surface outline-none ' +
  'data-[focused]:bg-surface-container-high data-[focused]:text-primary'

/** Menú del usuario con sus iniciales, nombre y rol (FR-038, FR-056). */
export function UserMenu({ usuario }: { usuario: UsuarioSalida }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return (
    <MenuTrigger>
      <Button
        aria-label={`Menú de ${usuario.nombre}`}
        className="flex items-center gap-2 outline-none data-[focus-visible]:outline data-[focus-visible]:outline-1 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-tertiary"
      >
        <span className="flex size-10 items-center justify-center border border-outline-variant bg-surface-container-high label-lg text-on-surface">
          {iniciales(usuario.nombre)}
        </span>
        <ChevronDown aria-hidden="true" className="size-4 text-on-surface-variant" />
      </Button>
      <Popover
        placement="bottom end"
        className="w-64 border border-primary-container bg-surface-container-lowest"
      >
        <div className="border-b border-primary-container/18 px-4 py-3">
          <p className="title-md text-on-surface">{usuario.nombre}</p>
          <p className="label-sm text-primary">{ROLES[usuario.rol]}</p>
        </div>
        <Menu
          aria-label="Opciones de usuario"
          className="py-1 outline-none"
          onAction={(clave) => {
            if (clave === 'cuenta') {
              void navigate({ to: '/cuenta' })
            } else {
              void cerrarSesion(queryClient).finally(() => {
                void navigate({ to: '/acceso' })
              })
            }
          }}
        >
          <MenuItem id="cuenta" className={claseItem}>
            <UserRound aria-hidden="true" className="size-4" />
            Mi cuenta
          </MenuItem>
          <Separator className="my-1 h-px bg-primary-container/18" />
          <MenuItem id="salir" className={claseItem}>
            <LogOut aria-hidden="true" className="size-4" />
            Cerrar sesión
          </MenuItem>
        </Menu>
      </Popover>
    </MenuTrigger>
  )
}
