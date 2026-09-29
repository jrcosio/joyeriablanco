import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { ApiError } from '../../api/client'
import { parametrosFacturacionQuery } from '../../api/queries/configuracionFacturacion'
import { facturaQuery, useModificarFactura } from '../../api/queries/facturas'
import type { FacturaSalida, ParametrosFacturacionSalida } from '../../api/tipos'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { ModalDocumento } from '../../components/ui/ModalDocumento'
import { toast } from '../../components/ui/toast-store'
import { desdeApi, formatearCantidad } from '../../lib/dinero'
import { tipoIvaDe } from '../../lib/facturacion'
import { useClaveOperacion } from '../../lib/idempotencia'
import { CamposFactura } from './CamposFactura'
import {
  campoDelServidor,
  esquema,
  etiquetaCliente,
  lineasCuerpo,
  type ValoresFactura,
} from './factura-valores'
import { CargandoModal } from './FacturaModal'
import { MotivoModificacionDialog, type MotivoElegido } from './MotivoModificacionDialog'

function valoresDe(factura: FacturaSalida, hoy: string): ValoresFactura {
  return {
    fecha_expedicion: hoy,
    cliente_id: factura.cliente.id,
    lineas: factura.lineas.map((l) => ({
      unidades: formatearCantidad(desdeApi(l.unidades)),
      descripcion: l.descripcion,
      precio_unitario: formatearCantidad(desdeApi(l.precio_unitario)),
    })),
  }
}

function FormularioModificacion({
  factura,
  parametros,
  onCerrar,
  onModificada,
}: {
  factura: FacturaSalida
  parametros: ParametrosFacturacionSalida
  onCerrar: () => void
  onModificada: (nueva: FacturaSalida) => void
}) {
  const modificar = useModificarFactura()
  const { clave, renovar } = useClaveOperacion()
  const [nombreCliente, setNombreCliente] = useState<string | undefined>(
    etiquetaCliente(factura.cliente),
  )
  const [pidiendoMotivo, setPidiendoMotivo] = useState(false)
  const [descartando, setDescartando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const form = useForm<ValoresFactura>({
    resolver: zodResolver(esquema),
    defaultValues: valoresDe(factura, parametros.hoy),
  })
  const sucio = form.formState.isDirty

  const intentarCerrar = () => {
    if (sucio) setDescartando(true)
    else onCerrar()
  }

  const pedirMotivo = form.handleSubmit((valores) => {
    setError(null)
    if (!valores.cliente_id) {
      form.setError('cliente_id', { message: 'Elige el cliente.' })
      return
    }
    setPidiendoMotivo(true)
  })

  const guardar = async (elegido: MotivoElegido) => {
    const valores = form.getValues()
    if (!valores.cliente_id) return
    setError(null)
    try {
      const nueva = await modificar.mutateAsync({
        id: factura.id,
        body: {
          motivo: elegido.motivo,
          causa: elegido.causa,
          motivo_texto: elegido.motivo_texto,
          cliente_id: valores.cliente_id,
          fecha_expedicion: valores.fecha_expedicion,
          lineas: lineasCuerpo(valores.lineas),
        },
        clave,
      })
      renovar()
      setPidiendoMotivo(false)
      const efecto = elegido.motivo === 'no_debio_emitirse' ? 'anulada' : 'rectificada'
      toast(`Se ha emitido ${nueva.num_serie}. ${factura.num_serie} queda ${efecto}`)
      onModificada(nueva)
    } catch (e) {
      setPidiendoMotivo(false)
      if (!(e instanceof ApiError) || e.tipo === 'red') {
        setError(
          'No se ha podido guardar la modificación. Tus datos siguen aquí: vuelve a intentarlo, sin riesgo de duplicarla.',
        )
      } else if (e.tipo === 'validacion' && e.problema.errores?.length) {
        for (const [campo, mensaje] of Object.entries(e.porCampo)) {
          const destino = campoDelServidor(campo)
          if (destino) form.setError(destino, { message: mensaje })
          else setError(mensaje)
        }
      } else if (e.tipo === 'fecha-expedicion') {
        form.setError('fecha_expedicion', { message: e.message })
      } else if (e.tipo === 'cliente-no-facturable') {
        form.setError('cliente_id', { message: e.message })
      } else {
        setError(e.message)
      }
    }
  }

  return (
    <ModalDocumento
      title={`Modificar factura ${factura.num_serie}`}
      subtitle="Se generará la corrección que corresponda; la factura original no cambia."
      isOpen
      onOpenChange={(abierto) => {
        if (!abierto) intentarCerrar()
      }}
      footer={
        <>
          <Button variant="ghost" onPress={intentarCerrar} className="sm:mr-auto">
            Cancelar
          </Button>
          <Button onPress={() => void pedirMotivo()} isDisabled={modificar.isPending}>
            Guardar
          </Button>
        </>
      }
    >
      <CamposFactura
        form={form}
        parametros={parametros}
        fechaOperacion={factura.fecha_operacion ?? factura.fecha_expedicion}
        numeroAyuda="La factura nueva recibe el siguiente número de su serie."
        nombreCliente={nombreCliente}
        onNombreCliente={setNombreCliente}
        onSubmit={() => void pedirMotivo()}
        despues={<Alerta mensaje={error} />}
      />
      <MotivoModificacionDialog
        key={String(pidiendoMotivo)}
        isOpen={pidiendoMotivo}
        onOpenChange={setPidiendoMotivo}
        numSerie={factura.num_serie}
        esRectificativa={factura.rectifica_a !== null}
        proximoNumero={parametros.proximo_numero}
        ivaOriginal={tipoIvaDe(factura)}
        ivaVigente={parametros.iva_por_defecto}
        enviando={modificar.isPending}
        onConfirmar={(elegido) => void guardar(elegido)}
      />
      <Dialog
        title="¿Descartar los cambios?"
        role="alertdialog"
        isOpen={descartando}
        onOpenChange={setDescartando}
      >
        <p className="body-md text-on-surface-variant">
          Hay cambios sin guardar en esta modificación. Si cierras, se perderán.
        </p>
        <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            variant="secondary"
            onPress={() => {
              setDescartando(false)
            }}
          >
            Seguir editando
          </Button>
          <Button
            onPress={() => {
              // Se cierra el modal entero sin cerrar antes la confirmación: así el foco vuelve a
              // quien abrió el modal y no a un campo que va a desaparecer (FR-039).
              onCerrar()
            }}
          >
            Descartar
          </Button>
        </div>
      </Dialog>
    </ModalDocumento>
  )
}

/** Modal «Modificar factura» (US5; FR-023, FR-024): cliente y líneas editables. */
export function ModificarFacturaModal({
  facturaId,
  onCerrar,
  onModificada,
}: {
  facturaId: string
  onCerrar: () => void
  onModificada: (nueva: FacturaSalida) => void
}) {
  const parametros = useQuery(parametrosFacturacionQuery)
  const factura = useQuery(facturaQuery(facturaId))
  if (!parametros.data || !factura.data) {
    const error = factura.isError
      ? factura.error.message
      : parametros.isError
        ? 'No se han podido cargar los datos de facturación. Cierra y vuelve a intentarlo.'
        : null
    return <CargandoModal titulo="Modificar factura" error={error} onCerrar={onCerrar} />
  }
  if (factura.data.estado !== 'vigente') {
    const vigente = factura.data.vigente_actual
    return (
      <ModalDocumento
        title={`Modificar factura ${factura.data.num_serie}`}
        isOpen
        onOpenChange={(abierto) => {
          if (!abierto) onCerrar()
        }}
        footer={
          <Button variant="ghost" onPress={onCerrar}>
            Cerrar
          </Button>
        }
      >
        <p className="body-md text-on-surface">
          Solo se puede modificar la factura vigente: esta ya está {factura.data.estado}.{' '}
          {vigente ? (
            <Link
              to="/facturas/$facturaId"
              params={{ facturaId: vigente.id }}
              search
              className="text-primary underline underline-offset-4"
            >
              Ver {vigente.num_serie}
            </Link>
          ) : null}
        </p>
      </ModalDocumento>
    )
  }
  return (
    <FormularioModificacion
      factura={factura.data}
      parametros={parametros.data}
      onCerrar={onCerrar}
      onModificada={onModificada}
    />
  )
}
