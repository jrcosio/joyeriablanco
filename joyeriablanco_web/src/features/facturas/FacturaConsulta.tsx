import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { useState } from 'react'
import { ApiError } from '../../api/client'
import { facturaQuery, useAnularFactura } from '../../api/queries/facturas'
import type { FacturaSalida } from '../../api/tipos'
import { useSesion } from '../../auth/session'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { claseEnlaceSecundario } from '../../components/ui/enlace'
import { Chip } from '../../components/ui/Chip'
import { ModalDocumento } from '../../components/ui/ModalDocumento'
import { Skeleton } from '../../components/ui/Skeleton'
import { toast } from '../../components/ui/toast-store'
import { desdeApi, formatearCantidad, formatearEuros } from '../../lib/dinero'
import { CAUSAS_RECTIFICACION } from '../../lib/facturacion'
import { fechaCorta } from '../../lib/fechas'
import { useClaveOperacion } from '../../lib/idempotencia'
import { nombreConEstado } from '../../lib/usuarios'
import { AnularFacturaDialog } from './AnularFacturaDialog'
import { EnlacePresupuesto } from './EnlacePresupuesto'
import { EnlacesFactura, HistorialFactura } from './HistorialFactura'
import { ImprimirFactura } from './ImprimirFactura'
import { FichaDestinatario } from '../documentos/ResumenCliente'
import { TotalesDocumento } from '../documentos/TotalesDocumento'

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h3 className="title-lg text-on-surface">{titulo}</h3>
      {children}
    </section>
  )
}

function Lineas({ factura }: { factura: FacturaSalida }) {
  if (factura.lineas.length === 0) {
    return <p className="body-md text-on-surface-variant">Sin líneas: devolución total.</p>
  }
  return (
    <div className="overflow-x-auto border border-primary-container/18 bg-surface-container-low">
      <table className="w-full">
        <caption className="sr-only">Líneas de la factura {factura.num_serie}</caption>
        <thead className="bg-surface-container">
          <tr className="label-md text-on-surface-variant">
            <th scope="col" className="px-4 py-3 text-right">
              Unidades
            </th>
            <th scope="col" className="px-4 py-3 text-left">
              Descripción
            </th>
            <th scope="col" className="px-4 py-3 text-right">
              Precio unitario
            </th>
            <th scope="col" className="px-4 py-3 text-right">
              Importe
            </th>
          </tr>
        </thead>
        <tbody>
          {factura.lineas.map((linea) => (
            <tr key={linea.orden} className="border-t border-primary-container/10 body-md">
              <td className="px-4 py-3 text-right tabular-nums">
                {formatearCantidad(desdeApi(linea.unidades))}
              </td>
              <td className="px-4 py-3">{linea.descripcion}</td>
              <td className="px-4 py-3 text-right tabular-nums">
                {formatearEuros(desdeApi(linea.precio_unitario))}
              </td>
              <td className="px-4 py-3 text-right tabular-nums">
                {formatearEuros(desdeApi(linea.importe))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Marca del estado y del tipo (FR-026): anulada, rectificada o rectificativa R1/R4. */
function Marcas({ factura }: { factura: FacturaSalida }) {
  const marcas = [
    factura.estado === 'anulada' ? (
      <Chip key="a" tone="neutral">
        Anulada
      </Chip>
    ) : null,
    factura.estado === 'rectificada' ? (
      <Chip key="r" tone="neutral">
        Rectificada
      </Chip>
    ) : null,
    factura.rectifica_a ? (
      <Chip key="t" tone="warning">
        Rectificativa {factura.tipo_factura}
      </Chip>
    ) : null,
  ].filter(Boolean)
  return marcas.length ? <div className="flex flex-wrap gap-2">{marcas}</div> : null
}

/** Detalle de una factura emitida en modo consulta (FR-026, FR-038). */
export function FacturaDetalle({ factura }: { factura: FacturaSalida }) {
  const desglose = factura.totales.desglose[0]
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-3">
        <Marcas factura={factura} />
        <EnlacesFactura factura={factura} />
        <EnlacePresupuesto presupuesto={factura.presupuesto_origen} />
      </div>
      <Seccion titulo="Datos de emisión">
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div>
            <dt className="label-sm text-on-surface-variant">Nº de factura</dt>
            <dd className="body-md tabular-nums text-on-surface">{factura.num_serie}</dd>
          </div>
          <div>
            <dt className="label-sm text-on-surface-variant">Fecha</dt>
            <dd className="body-md tabular-nums text-on-surface">
              {fechaCorta(factura.fecha_expedicion)}
            </dd>
          </div>
          {factura.fecha_operacion ? (
            <div>
              <dt className="label-sm text-on-surface-variant">Fecha de la operación</dt>
              <dd className="body-md tabular-nums text-on-surface">
                {fechaCorta(factura.fecha_operacion)}
              </dd>
            </div>
          ) : null}
          <div>
            <dt className="label-sm text-on-surface-variant">Emitida por</dt>
            <dd className="body-md text-on-surface">{nombreConEstado(factura.emitida_por)}</dd>
          </div>
        </dl>
        <FichaDestinatario datos={factura.cliente} />
      </Seccion>
      {factura.rectifica_a ? (
        <Seccion titulo="Rectificación">
          <dl className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="md:col-span-3">
              <dt className="label-sm text-on-surface-variant">Causa</dt>
              <dd className="body-md text-on-surface">
                {CAUSAS_RECTIFICACION[factura.rectifica_a.causa]}
              </dd>
            </div>
            <div>
              <dt className="label-sm text-on-surface-variant">Base rectificada</dt>
              <dd className="body-md tabular-nums text-on-surface">
                {formatearEuros(desdeApi(factura.rectifica_a.base_rectificada))}
              </dd>
            </div>
            <div>
              <dt className="label-sm text-on-surface-variant">Cuota rectificada</dt>
              <dd className="body-md tabular-nums text-on-surface">
                {formatearEuros(desdeApi(factura.rectifica_a.cuota_rectificada))}
              </dd>
            </div>
          </dl>
        </Seccion>
      ) : null}
      <Seccion titulo="Detalle de la factura">
        <Lineas factura={factura} />
      </Seccion>
      <TotalesDocumento
        base={desdeApi(factura.totales.base_total)}
        cuota={desdeApi(factura.totales.cuota_total)}
        total={desdeApi(factura.totales.importe_total)}
        tipoIva={factura.oro_inversion ? null : (desglose?.tipo_iva ?? '0.00')}
        mencion={factura.mencion_exencion}
        iban={factura.emisor.iban}
      />
      <HistorialFactura factura={factura} />
    </div>
  )
}

/**
 * Modal de consulta de una factura emitida (FR-038): «Cerrar», «Imprimir» con sus casillas (003,
 * US1) y, si está vigente y quien la mira es administrador, «Anular» y «Modificar». Tras anular
 * sigue en la factura, ya anulada (FR-049).
 */
export function FacturaConsultaModal({
  facturaId,
  onCerrar,
}: {
  facturaId: string
  onCerrar: () => void
}) {
  const { usuario } = useSesion()
  const consulta = useQuery(facturaQuery(facturaId))
  const factura = consulta.data
  const anular = useAnularFactura()
  const { clave, renovar } = useClaveOperacion()
  const [anulando, setAnulando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const corregible = factura?.estado === 'vigente' && usuario.rol === 'administrador'

  const confirmarAnulacion = async (motivoTexto: string) => {
    if (!factura) return
    setError(null)
    try {
      await anular.mutateAsync({
        id: factura.id,
        body: { declaracion_no_debio_emitirse: true, motivo_texto: motivoTexto },
        clave,
      })
      renovar()
      setAnulando(false)
      const original = factura.rectifica_a?.factura.num_serie
      toast(
        original
          ? `Factura ${factura.num_serie} anulada. ${original} vuelve a estar vigente`
          : `Factura ${factura.num_serie} anulada`,
      )
    } catch (e) {
      setAnulando(false)
      setError(
        e instanceof ApiError && e.tipo !== 'red'
          ? e.message
          : 'No se ha podido completar la anulación. Vuelve a intentarlo: no se anulará dos veces.',
      )
    }
  }

  return (
    <ModalDocumento
      title={factura ? `Factura ${factura.num_serie}` : 'Factura'}
      isOpen
      onOpenChange={(abierto) => {
        if (!abierto) onCerrar()
      }}
      footer={
        <>
          <Button variant="ghost" onPress={onCerrar} className="sm:mr-auto">
            Cerrar
          </Button>
          {factura ? <ImprimirFactura factura={factura} /> : null}
          {factura && corregible ? (
            <>
              <Button
                variant="danger"
                onPress={() => {
                  setAnulando(true)
                }}
                isDisabled={anular.isPending}
              >
                Anular
              </Button>
              <Link
                to="/facturas/$facturaId/modificar"
                params={{ facturaId: factura.id }}
                search
                className={claseEnlaceSecundario}
              >
                Modificar
              </Link>
            </>
          ) : null}
        </>
      }
    >
      {consulta.isError ? (
        <Alerta mensaje={consulta.error.message} />
      ) : factura ? (
        <div className="flex flex-col gap-6">
          <Alerta mensaje={error} />
          <FacturaDetalle factura={factura} />
        </div>
      ) : (
        <div className="flex flex-col gap-5" aria-busy="true" aria-label="Cargando">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}
      {factura ? (
        <AnularFacturaDialog
          key={String(anulando)}
          isOpen={anulando}
          onOpenChange={setAnulando}
          numSerie={factura.num_serie}
          reactivara={factura.rectifica_a?.factura.num_serie}
          enviando={anular.isPending}
          onConfirmar={(motivo) => void confirmarAnulacion(motivo)}
        />
      ) : null}
    </ModalDocumento>
  )
}
