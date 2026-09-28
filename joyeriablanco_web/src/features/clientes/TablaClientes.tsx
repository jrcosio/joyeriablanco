import { Link } from '@tanstack/react-router'
import { Pencil } from 'lucide-react'
import type { ClienteResumenSalida } from '../../api/tipos'
import { Chip } from '../../components/ui/Chip'
import { Skeleton } from '../../components/ui/Skeleton'
import { accionesCabecera, accionesCelda, tablaDesplazable } from '../../components/ui/tabla'

const TIPO = { particular: 'Particular', empresa: 'Empresa' } as const

function NombreCliente({ cliente }: { cliente: ClienteResumenSalida }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="title-md text-on-surface">{cliente.nombre}</span>
      <span className="flex items-center gap-2">
        <span className="label-sm text-primary">{TIPO[cliente.tipo]}</span>
        {cliente.activo ? null : <Chip tone="danger">Inactivo</Chip>}
      </span>
    </div>
  )
}

function Editar({ cliente }: { cliente: ClienteResumenSalida }) {
  return (
    <Link
      to="/clientes/$clienteId"
      params={{ clienteId: cliente.id }}
      search
      aria-label={`Editar cliente ${cliente.nombre}`}
      className="inline-flex size-10 items-center justify-center border border-outline-variant bg-surface-container-high text-primary transition-colors hover:border-primary-container hover:bg-surface-container-highest"
    >
      <Pencil aria-hidden="true" className="size-4" />
    </Link>
  )
}

const celda = 'px-6 py-4 body-md text-on-surface align-middle'
const cabecera = 'px-6 py-4 text-left label-md text-on-surface-variant'

/**
 * Tabla en tableta y escritorio y tarjetas en móvil (FR-031, FR-059). Con el menú lateral fijo,
 * la provincia se oculta entre 1024 y 1279 px y el teléfono y el correo solo caben desde 1536 px;
 * la columna de acciones queda fija a la derecha (R-22). Sin columna "Facturas" hasta que exista
 * el módulo de facturas (FR-035).
 */
export function TablaClientes({
  clientes,
  cargando,
}: {
  clientes: readonly ClienteResumenSalida[]
  cargando: boolean
}) {
  if (cargando) {
    return (
      <div aria-busy="true" aria-label="Cargando clientes" className="flex flex-col">
        {Array.from({ length: 5 }, (_, i) => (
          <div
            key={i}
            className="flex h-[76px] items-center gap-6 border-b border-primary-container/18 px-6"
          >
            <Skeleton className="h-5 w-48" />
            <Skeleton className="hidden h-5 w-28 md:block" />
            <Skeleton className="hidden h-5 w-24 lg:block" />
            <Skeleton className="ml-auto size-10" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <>
      <div className={`hidden md:block ${tablaDesplazable}`}>
        <table className="w-full border-collapse">
          <caption className="sr-only">Listado de clientes</caption>
          <thead className="border-b border-primary-container/25 bg-surface-container">
            <tr>
              <th scope="col" className={cabecera}>
                Cliente
              </th>
              <th scope="col" className={cabecera}>
                NIF/CIF
              </th>
              <th scope="col" className={cabecera}>
                Localidad
              </th>
              <th scope="col" className={`${cabecera} lg:hidden xl:table-cell`}>
                Provincia
              </th>
              <th scope="col" className={`${cabecera} hidden 2xl:table-cell`}>
                Teléfono
              </th>
              <th scope="col" className={`${cabecera} hidden 2xl:table-cell`}>
                Correo
              </th>
              <th scope="col" className={`${cabecera} ${accionesCabecera} text-right`}>
                Acciones
              </th>
            </tr>
          </thead>
          <tbody>
            {clientes.map((cliente) => (
              <tr
                key={cliente.id}
                className="group border-b border-primary-container/18 transition-colors last:border-b-0 hover:bg-surface-container-high"
              >
                <td className={celda}>
                  <NombreCliente cliente={cliente} />
                </td>
                <td className={`${celda} tabular-nums`}>{cliente.identificacion_numero}</td>
                <td className={celda}>{cliente.localidad ?? '—'}</td>
                <td className={`${celda} lg:hidden xl:table-cell`}>
                  {cliente.provincia_nombre ?? '—'}
                </td>
                <td className={`${celda} hidden tabular-nums 2xl:table-cell`}>
                  {cliente.telefono ?? '—'}
                </td>
                <td className={`${celda} hidden 2xl:table-cell`}>
                  {cliente.correo ? (
                    <span title={cliente.correo} className="block max-w-56 truncate">
                      {cliente.correo}
                    </span>
                  ) : (
                    '—'
                  )}
                </td>
                <td className={`${celda} ${accionesCelda} text-right`}>
                  <Editar cliente={cliente} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul aria-label="Listado de clientes" className="flex flex-col md:hidden">
        {clientes.map((cliente) => (
          <li
            key={cliente.id}
            className="flex items-start justify-between gap-4 border-b border-primary-container/18 px-4 py-4 last:border-b-0"
          >
            <div className="flex min-w-0 flex-col gap-2">
              <NombreCliente cliente={cliente} />
              <p className="body-sm tabular-nums text-on-surface-variant">
                {cliente.identificacion_numero}
                {cliente.localidad ? ` · ${cliente.localidad}` : ''}
                {cliente.provincia_nombre ? ` (${cliente.provincia_nombre})` : ''}
              </p>
              {cliente.telefono || cliente.correo ? (
                <p className="break-all body-sm text-on-surface-variant">
                  {[cliente.telefono, cliente.correo].filter(Boolean).join(' · ')}
                </p>
              ) : null}
            </div>
            <Editar cliente={cliente} />
          </li>
        ))}
      </ul>
    </>
  )
}
