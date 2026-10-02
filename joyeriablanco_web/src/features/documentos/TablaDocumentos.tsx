import type { ReactNode } from 'react'
import { Skeleton } from '../../components/ui/Skeleton'
import { accionesCabecera, accionesCelda, tablaDesplazable } from '../../components/ui/tabla'
import { desdeApi, formatearEuros } from '../../lib/dinero'
import { fechaCorta } from '../../lib/fechas'

/** Lo que muestra la tabla de cada fila: lo comparten facturas y presupuestos (las vistas SQL). */
export interface FilaDocumento {
  id: string
  fecha: string
  cliente_nombre?: string | null
  identificacion?: string | null
  base: string
  cuota: string
  total: string
  oro_inversion: boolean
}

/** Clase del botón de acción de cada fila (icono de 40 × 40 px). */
export const claseAccion =
  'inline-flex size-10 items-center justify-center border border-outline-variant ' +
  'bg-surface-container-high text-primary transition-colors hover:border-primary-container ' +
  'hover:bg-surface-container-highest'

const euros = (importe: string) => formatearEuros(desdeApi(importe))

// Relleno de 16 px hasta 1280 px: con el menú lateral fijo, a 1024 px la tabla no cabría con 24.
const celda = 'px-4 py-4 body-md text-on-surface align-middle xl:px-6'
const cabeceraBase = 'px-4 py-4 label-md text-on-surface-variant xl:px-6'
const cabecera = `${cabeceraBase} text-left`
const cabeceraImporte = `${cabeceraBase} text-right`
const importe = 'text-right tabular-nums whitespace-nowrap'

/**
 * Tabla en tableta y escritorio y tarjetas en móvil (002, FR-033 y FR-049; 005, FR-024). Anchos
 * medidos con los datos de ejemplo, como en 001 R-22: a 768 y 1024 px (este con el menú lateral
 * fijo) solo caben número, fecha, cliente y total, con relleno de 16 px; el NIF cabe desde 1280 px,
 * y la base y el IVA desde 1440 px. La acción, fija a la derecha, se ve siempre (SC-008).
 *
 * El número (con sus marcas) y la acción los pone cada documento; `documentos` es el plural para
 * los nombres accesibles, p. ej. «facturas».
 */
export function TablaDocumentos<F extends FilaDocumento>({
  filas,
  cargando,
  documentos,
  numero,
  accion,
}: {
  filas: readonly F[]
  cargando: boolean
  documentos: string
  numero: (fila: F) => ReactNode
  accion: (fila: F) => ReactNode
}) {
  if (cargando) {
    return (
      <div aria-busy="true" aria-label={`Cargando ${documentos}`} className="flex flex-col">
        {Array.from({ length: 5 }, (_, i) => (
          <div
            key={i}
            className="flex h-[68px] items-center gap-6 border-b border-primary-container/18 px-6"
          >
            <Skeleton className="h-5 w-32" />
            <Skeleton className="hidden h-5 w-24 md:block" />
            <Skeleton className="h-5 w-48" />
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
          <caption className="sr-only">Listado de {documentos}</caption>
          <thead className="border-b border-primary-container/25 bg-surface-container">
            <tr>
              <th scope="col" className={cabecera}>
                Número
              </th>
              <th scope="col" className={cabecera}>
                Fecha
              </th>
              <th scope="col" className={cabecera}>
                Cliente
              </th>
              <th scope="col" className={`${cabecera} hidden xl:table-cell`}>
                NIF/CIF
              </th>
              <th scope="col" className={`${cabeceraImporte} hidden min-[1440px]:table-cell`}>
                Base imponible
              </th>
              <th scope="col" className={`${cabeceraImporte} hidden min-[1440px]:table-cell`}>
                IVA
              </th>
              <th scope="col" className={cabeceraImporte}>
                Total
              </th>
              <th scope="col" className={`${cabeceraImporte} ${accionesCabecera}`}>
                Acciones
              </th>
            </tr>
          </thead>
          <tbody>
            {filas.map((fila) => (
              <tr
                key={fila.id}
                className="group border-b border-primary-container/18 transition-colors last:border-b-0 hover:bg-surface-container-high"
              >
                <td className={celda}>{numero(fila)}</td>
                <td className={`${celda} whitespace-nowrap tabular-nums`}>
                  {fechaCorta(fila.fecha)}
                </td>
                <td className={celda}>{fila.cliente_nombre ?? 'Sin cliente'}</td>
                <td className={`${celda} hidden tabular-nums xl:table-cell`}>
                  {fila.identificacion ?? '—'}
                </td>
                <td className={`${celda} ${importe} hidden min-[1440px]:table-cell`}>
                  {euros(fila.base)}
                </td>
                <td className={`${celda} ${importe} hidden min-[1440px]:table-cell`}>
                  {/* Oro de inversión: sin IVA (FR-033, FR-052). */}
                  {fila.oro_inversion ? 'Exenta' : euros(fila.cuota)}
                </td>
                <td className={`${celda} ${importe}`}>{euros(fila.total)}</td>
                <td className={`${celda} ${accionesCelda} text-right`}>{accion(fila)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul aria-label={`Listado de ${documentos}`} className="flex flex-col md:hidden">
        {filas.map((fila) => (
          <li
            key={fila.id}
            className="flex items-start justify-between gap-4 border-b border-primary-container/18 px-4 py-4 last:border-b-0"
          >
            <div className="flex min-w-0 flex-col gap-2">
              {numero(fila)}
              <p className="body-md text-on-surface">{fila.cliente_nombre ?? 'Sin cliente'}</p>
              <p className="body-sm tabular-nums text-on-surface-variant">
                {fechaCorta(fila.fecha)} · {euros(fila.total)}
              </p>
            </div>
            {accion(fila)}
          </li>
        ))}
      </ul>
    </>
  )
}
