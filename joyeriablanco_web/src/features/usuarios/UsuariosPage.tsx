import { useQuery } from '@tanstack/react-query'
import { EllipsisVertical, UserPlus } from 'lucide-react'
import { useState } from 'react'
import { Menu, MenuItem, MenuTrigger, Popover } from 'react-aria-components'
import { ApiError } from '../../api/client'
import {
  useCambiarRol,
  useDesactivarUsuario,
  useReactivarUsuario,
  useRestablecerContrasena,
  usuariosQuery,
} from '../../api/queries/usuarios'
import type { Rol, UsuarioSalida } from '../../api/tipos'
import { useSesion } from '../../auth/session'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Chip } from '../../components/ui/Chip'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import { toast } from '../../components/ui/toast-store'
import { fechaHora } from '../../lib/fechas'
import { ContrasenaTemporalDialog } from './ContrasenaTemporalDialog'
import { UsuarioAltaDialog } from './UsuarioAltaDialog'

const ROL: Record<Rol, string> = { administrador: 'Administrador', empleado: 'Empleado' }

type Accion =
  | { tipo: 'rol'; usuario: UsuarioSalida }
  | { tipo: 'desactivar'; usuario: UsuarioSalida }
  | { tipo: 'restablecer'; usuario: UsuarioSalida }

const claseItem =
  'cursor-pointer px-4 py-2.5 body-md text-on-surface outline-none ' +
  'data-[focused]:bg-surface-container-high data-[focused]:text-primary'

function Estado({ usuario }: { usuario: UsuarioSalida }) {
  return (
    <span className="flex flex-wrap gap-2">
      <Chip tone={usuario.activo ? 'success' : 'danger'}>
        {usuario.activo ? 'Activo' : 'Inactivo'}
      </Chip>
      {usuario.bloqueado ? <Chip tone="warning">Bloqueado</Chip> : null}
      {usuario.contrasena_temporal ? <Chip tone="warning">Contraseña temporal</Chip> : null}
    </span>
  )
}

/** Configuración → Usuarios (US5; FR-014 a FR-017). Solo administradores. */
export function UsuariosPage() {
  const { usuario: yo } = useSesion()
  const lista = useQuery(usuariosQuery)
  const cambiarRol = useCambiarRol()
  const desactivar = useDesactivarUsuario()
  const reactivar = useReactivarUsuario()
  const restablecer = useRestablecerContrasena()
  const [alta, setAlta] = useState(false)
  const [accion, setAccion] = useState<Accion | null>(null)
  const [temporal, setTemporal] = useState<{ nombreUsuario: string; contrasena: string } | null>(
    null,
  )

  const ejecutar = async (operacion: () => Promise<unknown>, mensaje: string) => {
    try {
      await operacion()
      toast(mensaje)
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'No se ha podido completar la operación.', 'error')
    } finally {
      setAccion(null)
    }
  }

  const confirmar = () => {
    if (!accion) return
    const { usuario } = accion
    if (accion.tipo === 'rol') {
      const rol: Rol = usuario.rol === 'administrador' ? 'empleado' : 'administrador'
      void ejecutar(
        () => cambiarRol.mutateAsync({ id: usuario.id, rol }),
        `${usuario.nombre} ahora es ${ROL[rol].toLowerCase()}.`,
      )
    } else if (accion.tipo === 'desactivar') {
      void ejecutar(() => desactivar.mutateAsync(usuario.id), `${usuario.nombre} desactivado.`)
    } else {
      void restablecer
        .mutateAsync(usuario.id)
        .then((r) => {
          setTemporal({
            nombreUsuario: r.usuario.nombre_usuario,
            contrasena: r.contrasena_temporal,
          })
          toast('Contraseña restablecida. Sus sesiones se han cerrado.')
        })
        .catch((e: unknown) => {
          toast(e instanceof ApiError ? e.message : 'No se ha podido restablecer.', 'error')
        })
        .finally(() => {
          setAccion(null)
        })
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="body-md text-on-surface-variant">
          Alta de empleados y administradores, roles, bajas y restablecimiento de contraseñas.
        </p>
        <Button
          onPress={() => {
            setAlta(true)
          }}
          className="w-full sm:w-auto"
        >
          <UserPlus aria-hidden="true" className="size-4" />
          Nuevo usuario
        </Button>
      </div>

      <Card className="overflow-hidden bg-surface-container-low">
        {lista.isError ? (
          <ErrorState
            message={lista.error.message}
            onRetry={() => {
              void lista.refetch()
            }}
          />
        ) : lista.isPending ? (
          <div aria-busy="true" aria-label="Cargando usuarios" className="flex flex-col gap-3 p-6">
            {Array.from({ length: 3 }, (_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : (
          <table className="w-full border-collapse">
            <caption className="sr-only">Usuarios del sistema</caption>
            <thead className="border-b border-primary-container/25 bg-surface-container">
              <tr>
                {['Usuario', 'Rol', 'Estado', 'Último acceso', 'Acciones'].map((c, i) => (
                  <th
                    key={c}
                    scope="col"
                    className={`px-6 py-4 text-left label-md text-on-surface-variant ${
                      i === 1 || i === 3 ? 'hidden md:table-cell' : ''
                    } ${i === 4 ? 'text-right' : ''}`}
                  >
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {lista.data.map((usuario) => {
                const esYo = usuario.id === yo.id
                return (
                  <tr
                    key={usuario.id}
                    className="border-b border-primary-container/18 last:border-b-0 hover:bg-surface-container-high"
                  >
                    <td className="px-6 py-4">
                      <span className="flex flex-col gap-1">
                        <span className="title-md text-on-surface">
                          {usuario.nombre}
                          {esYo ? (
                            <span className="body-sm text-on-surface-variant"> (tú)</span>
                          ) : null}
                        </span>
                        <span className="body-sm text-on-surface-variant">
                          {usuario.nombre_usuario}
                        </span>
                      </span>
                    </td>
                    <td className="hidden px-6 py-4 label-sm text-primary md:table-cell">
                      {ROL[usuario.rol]}
                    </td>
                    <td className="px-6 py-4">
                      <Estado usuario={usuario} />
                    </td>
                    <td className="hidden px-6 py-4 body-md tabular-nums text-on-surface md:table-cell">
                      {usuario.ultimo_acceso_en ? fechaHora(usuario.ultimo_acceso_en) : 'Nunca'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <MenuTrigger>
                        <Button variant="icon" aria-label={`Acciones para ${usuario.nombre}`}>
                          <EllipsisVertical aria-hidden="true" className="size-4" />
                        </Button>
                        <Popover
                          placement="bottom end"
                          className="w-60 border border-primary-container bg-surface-container-lowest"
                        >
                          <Menu
                            aria-label={`Acciones para ${usuario.nombre}`}
                            className="py-1 outline-none"
                            disabledKeys={esYo ? ['rol', 'estado'] : []}
                            onAction={(clave) => {
                              if (clave === 'rol') setAccion({ tipo: 'rol', usuario })
                              if (clave === 'restablecer')
                                setAccion({ tipo: 'restablecer', usuario })
                              if (clave === 'estado') {
                                if (usuario.activo) {
                                  setAccion({ tipo: 'desactivar', usuario })
                                } else {
                                  void ejecutar(
                                    () => reactivar.mutateAsync(usuario.id),
                                    `${usuario.nombre} reactivado.`,
                                  )
                                }
                              }
                            }}
                          >
                            <MenuItem
                              id="rol"
                              className={`${claseItem} data-[disabled]:opacity-40`}
                            >
                              {usuario.rol === 'administrador'
                                ? 'Cambiar a empleado'
                                : 'Cambiar a administrador'}
                            </MenuItem>
                            <MenuItem id="restablecer" className={claseItem}>
                              Restablecer contraseña
                            </MenuItem>
                            <MenuItem
                              id="estado"
                              className={`${claseItem} data-[disabled]:opacity-40`}
                            >
                              {usuario.activo ? 'Desactivar' : 'Reactivar'}
                            </MenuItem>
                          </Menu>
                        </Popover>
                      </MenuTrigger>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </Card>

      <UsuarioAltaDialog
        isOpen={alta}
        onOpenChange={setAlta}
        onCreado={(resultado) => {
          setAlta(false)
          toast(`Usuario «${resultado.usuario.nombre_usuario}» creado.`)
          setTemporal({
            nombreUsuario: resultado.usuario.nombre_usuario,
            contrasena: resultado.contrasena_temporal,
          })
        }}
      />

      <ConfirmDialog
        isOpen={accion !== null}
        onOpenChange={(abierto) => {
          if (!abierto) setAccion(null)
        }}
        onConfirm={confirmar}
        destructive={accion?.tipo === 'desactivar'}
        title={
          accion?.tipo === 'rol'
            ? '¿Cambiar el rol?'
            : accion?.tipo === 'desactivar'
              ? '¿Desactivar el usuario?'
              : '¿Restablecer la contraseña?'
        }
        confirmLabel={
          accion?.tipo === 'rol'
            ? 'Cambiar rol'
            : accion?.tipo === 'desactivar'
              ? 'Desactivar'
              : 'Restablecer'
        }
      >
        {accion?.tipo === 'rol'
          ? `${accion.usuario.nombre} pasará a ser ${
              accion.usuario.rol === 'administrador' ? 'empleado' : 'administrador'
            }. Sus sesiones abiertas se cerrarán.`
          : accion?.tipo === 'desactivar'
            ? `${accion.usuario.nombre} no podrá acceder y sus sesiones abiertas se cerrarán al momento.`
            : accion
              ? `Se generará una contraseña temporal para ${accion.usuario.nombre}, se levantará su bloqueo si lo tiene y se cerrarán sus sesiones.`
              : null}
      </ConfirmDialog>

      <ContrasenaTemporalDialog
        datos={temporal}
        onCerrar={() => {
          setTemporal(null)
        }}
      />
    </div>
  )
}
