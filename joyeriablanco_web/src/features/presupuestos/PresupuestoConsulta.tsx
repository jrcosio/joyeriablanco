import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { TriangleAlert } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { ApiError, type Problema } from '../../api/client'
import { presupuestoQuery, useAnularPresupuesto } from '../../api/queries/presupuestos'
import type { PresupuestoSalida } from '../../api/tipos'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { claseEnlaceSecundario } from '../../components/ui/enlace'
import { ModalDocumento } from '../../components/ui/ModalDocumento'
import { Skeleton } from '../../components/ui/Skeleton'
import { toast } from '../../components/ui/toast-store'
import { useSesion } from '../../auth/session'
import { desdeApi } from '../../lib/dinero'
import { fechaCorta } from '../../lib/fechas'
import { useClaveOperacion } from '../../lib/idempotencia'
import { nombreConEstado } from '../../lib/usuarios'
import { Seccion } from '../documentos/CamposDocumento'
import { LineasSoloLectura } from '../documentos/LineasSoloLectura'
import { FichaDestinatario } from '../documentos/ResumenCliente'
import { TotalesDocumento } from '../documentos/TotalesDocumento'
import { AnularPresupuestoDialog } from './AnularPresupuestoDialog'
import { ConvertirPresupuestoDialog } from './ConvertirPresupuestoDialog'
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

/** «Abrir borrador de factura»: el borrador vinculado de un presupuesto en facturación (FR-020). */
function AbrirBorradorFactura({ borradorId }: { borradorId: string }) {
  return (
    <Link
      to="/facturas/borradores/$borradorId"
      params={{ borradorId }}
      className={`${claseEnlaceSecundario} self-start`}
    >
      Abrir borrador de factura
    </Link>
  )
}

/** Un presupuesto en facturación no se modifica ni se anula hasta emitir o eliminar su borrador. */
function AvisoEnFacturacion({ borradorId }: { borradorId: string }) {
  return (
    <div
      role="status"
      className="flex flex-col gap-3 border border-warning/40 bg-warning/8 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="flex items-start gap-3 body-md text-on-surface">
        <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-warning" />
        Este presupuesto tiene un borrador de factura en curso.
      </p>
      <AbrirBorradorFactura borradorId={borradorId} />
    </div>
  )
}

/** Detalle de un presupuesto emitido en modo consulta (FR-017, FR-026). Nada es editable. */
export function PresupuestoDetalle({ presupuesto }: { presupuesto: PresupuestoSalida }) {
  const desglose = presupuesto.totales.desglose[0]
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-3">
        {/* Un pendiente no lleva marca: sin la fila vacía, que dejaría un hueco arriba. */}
        {presupuesto.estado !== 'pendiente' ? (
          <div className="flex flex-wrap gap-2">
            <MarcaPresupuesto estado={presupuesto.estado} />
          </div>
        ) : null}
        <EnlacesPresupuesto presupuesto={presupuesto} />
        {presupuesto.estado === 'en_facturacion' && presupuesto.borrador_factura ? (
          <AvisoEnFacturacion borradorId={presupuesto.borrador_factura.id} />
        ) : null}
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

/** El 409 `presupuesto-no-modificable`: qué ha pasado y, si está en facturación, su borrador. */
function AvisoNoModificable({ problema }: { problema: Problema }) {
  const borradorId =
    typeof problema.borrador_factura_id === 'string' ? problema.borrador_factura_id : null
  return (
    <div className="flex flex-col gap-3">
      <Alerta mensaje={`${problema.detail ?? problema.title} Se muestran sus datos actuales.`} />
      {borradorId ? <AbrirBorradorFactura borradorId={borradorId} /> : null}
    </div>
  )
}

/**
 * Un pendiente o un caducado se puede convertir, con aviso si caducó (FR-018), y un administrador
 * lo puede modificar o anular (FR-015, FR-016). En facturación o cerrado, nada de eso.
 */
const ABIERTOS: readonly PresupuestoSalida['estado'][] = ['pendiente', 'caducado']

/**
 * Modal de consulta de un presupuesto emitido (FR-027): «Cerrar», «Imprimir» (US2), «Convertir en
 * factura» (US3) y, para un administrador, «Anular» y «Modificar» (US4). Tras anular sigue en el
 * presupuesto, ya marcado.
 */
export function PresupuestoConsultaModal({
  presupuestoId,
  onCerrar,
}: {
  presupuestoId: string
  onCerrar: () => void
}) {
  const { usuario } = useSesion()
  const queryClient = useQueryClient()
  const consulta = useQuery(presupuestoQuery(presupuestoId))
  const presupuesto = consulta.data
  const anular = useAnularPresupuesto()
  const { clave, renovar } = useClaveOperacion()
  const [convirtiendo, setConvirtiendo] = useState(false)
  const [anulando, setAnulando] = useState(false)
  const [noModificable, setNoModificable] = useState<Problema | null>(null)
  const [error, setError] = useState<string | null>(null)
  const abierto = presupuesto ? ABIERTOS.includes(presupuesto.estado) : false
  const administrador = usuario.rol === 'administrador'

  const alNoModificable = (problema: Problema) => {
    setNoModificable(problema)
    void queryClient.invalidateQueries({ queryKey: presupuestoQuery(presupuestoId).queryKey })
  }

  const confirmarAnulacion = async (motivoTexto: string) => {
    if (!presupuesto) return
    setError(null)
    setNoModificable(null)
    try {
      await anular.mutateAsync({ id: presupuesto.id, body: { motivo_texto: motivoTexto }, clave })
      renovar()
      setAnulando(false)
      toast(`Presupuesto ${presupuesto.num_serie} anulado`)
    } catch (e) {
      setAnulando(false)
      if (e instanceof ApiError && e.tipo === 'presupuesto-no-modificable') {
        alNoModificable(e.problema)
      } else {
        setError(
          e instanceof ApiError && e.tipo !== 'red'
            ? e.message
            : 'No se ha podido completar la anulación. Vuelve a intentarlo: no se anulará dos veces.',
        )
      }
    }
  }

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
          {presupuesto && abierto && administrador ? (
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
                to="/presupuestos/$presupuestoId/modificar"
                params={{ presupuestoId: presupuesto.id }}
                search
                className={claseEnlaceSecundario}
              >
                Modificar
              </Link>
            </>
          ) : null}
          {presupuesto && abierto ? (
            <Button
              onPress={() => {
                setNoModificable(null)
                setConvirtiendo(true)
              }}
            >
              Convertir en factura
            </Button>
          ) : null}
        </>
      }
    >
      {consulta.isError ? (
        <Alerta mensaje={consulta.error.message} />
      ) : presupuesto ? (
        <div className="flex flex-col gap-6">
          {noModificable ? <AvisoNoModificable problema={noModificable} /> : null}
          <Alerta mensaje={error} />
          <PresupuestoDetalle presupuesto={presupuesto} />
          <ConvertirPresupuestoDialog
            presupuesto={presupuesto}
            isOpen={convirtiendo}
            onOpenChange={setConvirtiendo}
            onNoModificable={alNoModificable}
          />
          <AnularPresupuestoDialog
            key={String(anulando)}
            isOpen={anulando}
            onOpenChange={setAnulando}
            numSerie={presupuesto.num_serie}
            enviando={anular.isPending}
            onConfirmar={(motivo) => void confirmarAnulacion(motivo)}
          />
        </div>
      ) : (
        <div className="flex flex-col gap-5" aria-busy="true" aria-label="Cargando">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}
    </ModalDocumento>
  )
}
