import { Link } from '@tanstack/react-router'
import { Eye, Pencil } from 'lucide-react'
import type { PresupuestoResumenSalida } from '../../api/tipos'
import { claseAccion, TablaDocumentos } from '../documentos/TablaDocumentos'
import { MarcaPresupuesto } from './MarcaPresupuesto'

/** Número del presupuesto, o la marca «Borrador», con la marca de su estado (FR-024). */
function Numero({ fila }: { fila: PresupuestoResumenSalida }) {
  if (fila.tipo_documento === 'borrador') {
    return <MarcaPresupuesto estado="borrador" className="self-start" />
  }
  return (
    <span className="flex flex-wrap items-center gap-2">
      <span className="title-md whitespace-nowrap tabular-nums text-on-surface">
        {fila.num_serie}
      </span>
      <MarcaPresupuesto estado={fila.estado} />
    </span>
  )
}

/** Acción de la fila con nombre accesible (FR-026): abrir el borrador o ver el presupuesto. */
function Accion({ fila }: { fila: PresupuestoResumenSalida }) {
  if (fila.tipo_documento === 'borrador' || !fila.num_serie) {
    return (
      <Link
        to="/presupuestos/borradores/$borradorId"
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
      to="/presupuestos/$presupuestoId"
      params={{ presupuestoId: fila.id }}
      search
      aria-label={`Ver presupuesto ${fila.num_serie}`}
      className={claseAccion}
    >
      <Eye aria-hidden="true" className="size-4" />
    </Link>
  )
}

/** Listado de presupuestos: la tabla común de documentos (R-13), con sus anchos medidos. */
export function TablaPresupuestos({
  filas,
  cargando,
}: {
  filas: readonly PresupuestoResumenSalida[]
  cargando: boolean
}) {
  return (
    <TablaDocumentos
      filas={filas}
      cargando={cargando}
      documentos="presupuestos"
      numero={(fila) => <Numero fila={fila} />}
      accion={(fila) => <Accion fila={fila} />}
    />
  )
}
