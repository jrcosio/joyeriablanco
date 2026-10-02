import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { presupuestoQuery } from '../../api/queries/presupuestos'
import type { PresupuestoSalida } from '../../api/tipos'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { ModalDocumento } from '../../components/ui/ModalDocumento'
import { Skeleton } from '../../components/ui/Skeleton'
import { desdeApi } from '../../lib/dinero'
import { fechaCorta } from '../../lib/fechas'
import { nombreConEstado } from '../../lib/usuarios'
import { Seccion } from '../documentos/CamposDocumento'
import { LineasSoloLectura } from '../documentos/LineasSoloLectura'
import { FichaDestinatario } from '../documentos/ResumenCliente'
import { TotalesDocumento } from '../documentos/TotalesDocumento'
import { EnlacesPresupuesto, HistorialPresupuesto } from './HistorialPresupuesto'
import { ImprimirPresupuesto } from './ImprimirPresupuesto'
import { MarcaPresupuesto } from './MarcaPresupuesto'

function Dato({ etiqueta, children }: { etiqueta: string; children: ReactNode }) {
  return (
    <div>
      <dt className="label-sm text-on-surface-variant">{etiqueta}</dt>
      <dd className="body-md tabular-nums text-on-surface">{children}</dd>
    </div>
  )
}

/** Detalle de un presupuesto emitido en modo consulta (FR-017, FR-026). Nada es editable. */
export function PresupuestoDetalle({ presupuesto }: { presupuesto: PresupuestoSalida }) {
  const desglose = presupuesto.totales.desglose[0]
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap gap-2">
          <MarcaPresupuesto estado={presupuesto.estado} />
        </div>
        <EnlacesPresupuesto presupuesto={presupuesto} />
      </div>
      <Seccion titulo="Datos del presupuesto">
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Dato etiqueta="Nº de presupuesto">{presupuesto.num_serie}</Dato>
          <Dato etiqueta="Fecha">{fechaCorta(presupuesto.fecha)}</Dato>
          <Dato etiqueta="Válido hasta">{fechaCorta(presupuesto.valido_hasta)}</Dato>
          <Dato etiqueta="Emitido por">{nombreConEstado(presupuesto.emitido_por)}</Dato>
        </dl>
        <FichaDestinatario datos={presupuesto.cliente} />
      </Seccion>
      <Seccion titulo="Detalle del presupuesto">
        <LineasSoloLectura
          lineas={presupuesto.lineas}
          titulo={`Líneas del presupuesto ${presupuesto.num_serie}`}
        />
      </Seccion>
      <TotalesDocumento
        base={desdeApi(presupuesto.totales.base_total)}
        cuota={desdeApi(presupuesto.totales.cuota_total)}
        total={desdeApi(presupuesto.totales.importe_total)}
        tipoIva={presupuesto.oro_inversion ? null : (desglose?.tipo_iva ?? '0.00')}
        mencion={presupuesto.mencion_exencion}
        titulo="Total presupuesto"
      />
      <HistorialPresupuesto presupuesto={presupuesto} />
    </div>
  )
}

/**
 * Modal de consulta de un presupuesto emitido (FR-027). Las acciones se suman en cada historia:
 * imprimir (US2), convertir en factura (US3), y modificar y anular (US4).
 */
export function PresupuestoConsultaModal({
  presupuestoId,
  onCerrar,
}: {
  presupuestoId: string
  onCerrar: () => void
}) {
  const consulta = useQuery(presupuestoQuery(presupuestoId))
  const presupuesto = consulta.data

  return (
    <ModalDocumento
      title={presupuesto ? `Presupuesto ${presupuesto.num_serie}` : 'Presupuesto'}
      isOpen
      onOpenChange={(abierto) => {
        if (!abierto) onCerrar()
      }}
      footer={
        <>
          <Button variant="ghost" onPress={onCerrar} className="sm:mr-auto">
            Cerrar
          </Button>
          {presupuesto ? <ImprimirPresupuesto presupuesto={presupuesto} /> : null}
        </>
      }
    >
      {consulta.isError ? (
        <Alerta mensaje={consulta.error.message} />
      ) : presupuesto ? (
        <PresupuestoDetalle presupuesto={presupuesto} />
      ) : (
        <div className="flex flex-col gap-5" aria-busy="true" aria-label="Cargando">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}
    </ModalDocumento>
  )
}
