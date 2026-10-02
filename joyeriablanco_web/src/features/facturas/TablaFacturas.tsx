import { Link } from '@tanstack/react-router'
import { Eye, Pencil } from 'lucide-react'
import type { FacturaResumenSalida } from '../../api/tipos'
import { Chip } from '../../components/ui/Chip'
import { claseAccion, TablaDocumentos } from '../documentos/TablaDocumentos'

/** Número de la factura, o la marca «Borrador», con la marca de anulada o rectificada (FR-033). */
function Numero({ fila }: { fila: FacturaResumenSalida }) {
  if (fila.tipo_documento === 'borrador') {
    return (
      <Chip tone="warning" className="self-start">
        Borrador
      </Chip>
    )
  }
  return (
    <span className="flex flex-wrap items-center gap-2">
      <span className="title-md whitespace-nowrap tabular-nums text-on-surface">
        {fila.num_serie}
      </span>
      {fila.estado === 'anulada' ? <Chip tone="neutral">Anulada</Chip> : null}
      {fila.estado === 'rectificada' ? <Chip tone="neutral">Rectificada</Chip> : null}
    </span>
  )
}

/** Acción de la fila con nombre accesible (FR-049): abrir el borrador o ver la factura. */
function Accion({ fila }: { fila: FacturaResumenSalida }) {
  if (fila.tipo_documento === 'borrador' || !fila.num_serie) {
    return (
      <Link
        to="/facturas/borradores/$borradorId"
        params={{ borradorId: fila.id }}
        search
        aria-label={`Abrir borrador de ${fila.cliente_nombre ?? 'sin cliente'}`}
        className={claseAccion}
      >
        <Pencil aria-hidden="true" className="size-4" />
      </Link>
    )
  }
  return (
    <Link
      to="/facturas/$facturaId"
      params={{ facturaId: fila.id }}
      search
      aria-label={`Ver factura ${fila.num_serie}`}
      className={claseAccion}
    >
      <Eye aria-hidden="true" className="size-4" />
    </Link>
  )
}

/** Listado de facturas: la tabla común con el número, sus marcas y la acción de factura. */
export function TablaFacturas({
  filas,
  cargando,
}: {
  filas: readonly FacturaResumenSalida[]
  cargando: boolean
}) {
  return (
    <TablaDocumentos
      filas={filas}
      cargando={cargando}
      documentos="facturas"
      numero={(fila) => <Numero fila={fila} />}
      accion={(fila) => <Accion fila={fila} />}
    />
  )
}
