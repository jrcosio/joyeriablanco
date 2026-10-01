import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery } from '@tanstack/react-query'
import { TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { Form } from 'react-aria-components'
import { z } from 'zod'
import { ApiError } from '../../api/client'
import {
  configuracionFacturacionQuery,
  useGuardarConfiguracionFacturacion,
} from '../../api/queries/configuracionFacturacion'
import type {
  ConfiguracionFacturacionEntrada,
  ConfiguracionFacturacionSalida,
} from '../../api/tipos'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { CampoDecimal } from '../../components/ui/CampoDecimal'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { ErrorState } from '../../components/ui/ErrorState'
import { Select } from '../../components/ui/Select'
import { Skeleton } from '../../components/ui/Skeleton'
import { TextField } from '../../components/ui/TextField'
import { toast } from '../../components/ui/toast-store'
import { aApi, parsearEntrada } from '../../lib/dinero'
import {
  formatearIban,
  listaTiposIva,
  MODALIDADES,
  normalizarIban,
  textoFalta,
  textoTipoIva,
  tipoIvaATexto,
} from '../../lib/facturacion'
import { AjusteContadorDialog } from './AjusteContadorDialog'

/** De 0 a 99,99, con dos decimales como mucho (FR-001, research R-20): en centésimas. */
const IVA_MAXIMO = 9999n
const ERROR_IVA = 'Escribe un porcentaje entre 0 y 99,99, con dos decimales como mucho.'

/** El tipo escrito, como lo espera la API («22.00»), o `null` si no es válido. */
function tipoEscrito(texto: string): string | null {
  const valor = parsearEntrada(texto)
  return valor === null || valor > IVA_MAXIMO ? null : aApi(valor)
}

const esquema = z.object({
  iva_por_defecto: z.string().refine((v) => tipoEscrito(v) !== null, ERROR_IVA),
  modalidad: z.enum(['', 'verifactu', 'no_verifactu']),
  nombre: z.string().max(120),
  nif: z.string().max(20),
  direccion: z.string().max(200),
  codigo_postal: z.string().max(10),
  localidad: z.string().max(100),
  iban: z.string().max(42),
})
type Valores = z.infer<typeof esquema>
type CampoFormulario = keyof Valores

const CAMPO_DEL_SERVIDOR: Record<string, CampoFormulario> = {
  iva_por_defecto: 'iva_por_defecto',
  modalidad: 'modalidad',
  'emisor.nombre': 'nombre',
  'emisor.nif': 'nif',
  'emisor.direccion': 'direccion',
  'emisor.codigo_postal': 'codigo_postal',
  'emisor.localidad': 'localidad',
  'emisor.iban': 'iban',
}

function valoresIniciales(config: ConfiguracionFacturacionSalida): Valores {
  return {
    iva_por_defecto: tipoIvaATexto(config.iva_por_defecto),
    modalidad: config.modalidad ?? '',
    nombre: config.emisor.nombre ?? '',
    nif: config.emisor.nif ?? '',
    direccion: config.emisor.direccion ?? '',
    codigo_postal: config.emisor.codigo_postal ?? '',
    localidad: config.emisor.localidad ?? '',
    iban: formatearIban(config.emisor.iban ?? ''),
  }
}

const vacioANulo = (valor: string) => (valor.trim() === '' ? null : valor.trim())

function aCuerpo(
  valores: Valores,
  version: number,
  confirmarTipoIva: boolean,
): ConfiguracionFacturacionEntrada {
  return {
    version,
    iva_por_defecto: tipoEscrito(valores.iva_por_defecto) ?? valores.iva_por_defecto,
    confirmar_tipo_iva: confirmarTipoIva,
    modalidad: valores.modalidad === '' ? null : valores.modalidad,
    emisor: {
      nombre: vacioANulo(valores.nombre),
      nif: vacioANulo(valores.nif),
      direccion: vacioANulo(valores.direccion),
      codigo_postal: vacioANulo(valores.codigo_postal),
      localidad: vacioANulo(valores.localidad),
      iban: vacioANulo(normalizarIban(valores.iban)),
    },
  }
}

/** Aviso, mientras se escribe, de un tipo que no está en la lista oficial de hoy (R-20). */
function AvisoTipoIva({ texto, oficiales }: { texto: string; oficiales: readonly string[] }) {
  const tipo = tipoEscrito(texto)
  if (tipo === null || oficiales.includes(tipo)) return null
  return (
    <p role="status" className="body-sm text-warning">
      {textoTipoIva(tipo)} no está entre los tipos que admite hoy la AEAT (
      {listaTiposIva(oficiales)}).
    </p>
  )
}

function AvisoEmision({ faltan }: { faltan: readonly string[] }) {
  if (faltan.length === 0) return null
  return (
    <div
      role="status"
      aria-labelledby="aviso-emision"
      className="flex items-start gap-3 border border-warning/40 bg-warning/8 px-4 py-3"
    >
      <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-warning" />
      <div className="flex flex-col gap-1">
        <p id="aviso-emision" className="title-md text-on-surface">
          Todavía no se puede emitir ninguna factura
        </p>
        <p className="body-md text-on-surface-variant">
          Falta: {faltan.map(textoFalta).join(', ')}.
        </p>
      </div>
    </div>
  )
}

function Formulario({ config }: { config: ConfiguracionFacturacionSalida }) {
  const guardar = useGuardarConfiguracionFacturacion()
  const [error, setError] = useState<string | null>(null)
  // Valores pendientes de confirmar por un tipo fuera de la lista oficial (R-20).
  const [porConfirmar, setPorConfirmar] = useState<Valores | null>(null)
  const {
    control,
    handleSubmit,
    setError: marcar,
  } = useForm<Valores>({
    resolver: zodResolver(esquema),
    defaultValues: valoresIniciales(config),
  })

  const guardarValores = async (valores: Valores, confirmarTipoIva: boolean) => {
    setError(null)
    try {
      await guardar.mutateAsync(aCuerpo(valores, config.version, confirmarTipoIva))
      toast('Configuración de facturación guardada')
    } catch (e) {
      if (e instanceof ApiError && e.tipo === 'validacion' && e.problema.errores?.length) {
        for (const [campo, mensaje] of Object.entries(e.porCampo)) {
          const destino = CAMPO_DEL_SERVIDOR[campo]
          if (destino) marcar(destino, { message: mensaje })
          else setError(mensaje)
        }
      } else if (e instanceof ApiError && e.tipo === 'tipo-iva-sin-confirmar') {
        setPorConfirmar(valores)
      } else {
        setError(e instanceof ApiError ? e.message : 'No se ha podido guardar la configuración.')
      }
    }
  }

  const enviar = handleSubmit((valores) => guardarValores(valores, false))
  const tipoPendiente = porConfirmar ? tipoEscrito(porConfirmar.iva_por_defecto) : null

  const texto = (
    name: 'nombre' | 'nif' | 'direccion' | 'codigo_postal' | 'localidad',
    label: string,
    extra: { className?: string; inputMode?: 'numeric' } = {},
  ) => (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <TextField
          label={label}
          value={field.value}
          onChange={field.onChange}
          onBlur={field.onBlur}
          error={fieldState.error?.message}
          {...extra}
        />
      )}
    />
  )

  return (
    <Form
      className="flex flex-col gap-8"
      validationBehavior="aria"
      onSubmit={(e) => {
        e.preventDefault()
        void enviar()
      }}
    >
      <fieldset className="flex flex-col gap-5">
        <legend className="mb-4 label-md text-primary">Impuestos y modalidad</legend>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          <Controller
            control={control}
            name="iva_por_defecto"
            render={({ field, fieldState }) => (
              <div className="flex flex-col gap-1.5">
                <CampoDecimal
                  label="IVA por defecto"
                  sufijo="%"
                  isRequired
                  value={field.value}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                  error={fieldState.error?.message}
                />
                <AvisoTipoIva texto={field.value} oficiales={config.tipos_iva_oficiales} />
              </div>
            )}
          />
          <Controller
            control={control}
            name="modalidad"
            render={({ field, fieldState }) => (
              <div className="flex flex-col gap-1.5 md:col-span-3">
                <Select
                  label="Modalidad del sistema de facturación"
                  options={MODALIDADES.map((m) => ({
                    id: m.id === '' ? 'sin-decidir' : m.id,
                    label: m.label,
                  }))}
                  value={field.value === '' ? 'sin-decidir' : field.value}
                  onChange={(v) => {
                    field.onChange(v === 'sin-decidir' || v === null ? '' : v)
                  }}
                  isDisabled={config.modalidad_bloqueada}
                  error={fieldState.error?.message}
                />
                <p className="body-sm text-on-surface-variant">
                  {config.modalidad_bloqueada
                    ? 'Ya hay registros de facturación: el cambio de modalidad llega con la remisión a la AEAT, que gestiona la permanencia y la renuncia.'
                    : 'Pendiente de la asesoría. Hace falta elegirla para emitir.'}
                </p>
              </div>
            )}
          />
        </div>
        <p className="body-sm text-on-surface-variant">
          El IVA se aplica a todas las líneas de las facturas nuevas, salvo en las de oro de
          inversión, que van sin IVA. Cambiarlo no altera las ya emitidas.
        </p>
      </fieldset>

      <fieldset className="flex flex-col gap-5 border-t border-primary-container/18 pt-5">
        <legend className="mb-4 label-md text-primary">Datos del emisor</legend>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          {texto('nombre', 'Nombre o razón social', { className: 'md:col-span-2' })}
          {texto('nif', 'NIF')}
          {texto('direccion', 'Dirección')}
          {texto('codigo_postal', 'Código postal', { inputMode: 'numeric' })}
          {texto('localidad', 'Localidad')}
          <div className="flex flex-col gap-1.5">
            <span className="label-md text-on-surface-variant">Provincia</span>
            <span className="body-md text-on-surface">
              {config.emisor.provincia ?? 'Se deduce del código postal'}
            </span>
          </div>
          <Controller
            control={control}
            name="iban"
            render={({ field, fieldState }) => (
              <TextField
                label="IBAN"
                description="Opcional. Sale en las facturas para que el cliente pueda pagar por transferencia."
                value={field.value}
                onChange={field.onChange}
                onBlur={() => {
                  field.onChange(formatearIban(field.value))
                  field.onBlur()
                }}
                error={fieldState.error?.message}
                autoComplete="off"
                className="md:col-span-2"
              />
            )}
          />
        </div>
      </fieldset>

      <Alerta mensaje={error} />
      <div className="flex justify-end">
        <Button type="submit" isDisabled={guardar.isPending}>
          {guardar.isPending ? 'Guardando…' : 'Guardar configuración'}
        </Button>
      </div>
      <ConfirmDialog
        title="¿Guardar un tipo de IVA que la AEAT no admite hoy?"
        isOpen={porConfirmar !== null}
        onOpenChange={(abierto) => {
          if (!abierto) setPorConfirmar(null)
        }}
        confirmLabel="Guardar igualmente"
        isPending={guardar.isPending}
        onConfirm={() => {
          const valores = porConfirmar
          setPorConfirmar(null)
          if (valores) void guardarValores(valores, true)
        }}
      >
        <p>
          {tipoPendiente ? textoTipoIva(tipoPendiente) : 'Ese tipo'} no está entre los tipos que
          admite hoy la AEAT ({listaTiposIva(config.tipos_iva_oficiales)}). Guárdalo solo si ha
          cambiado la ley: hasta que la AEAT lo admita, podría rechazar los registros de las
          facturas.
        </p>
      </ConfirmDialog>
    </Form>
  )
}

/** Configuración → Facturación, solo administradores (US1; FR-001 a FR-004, FR-010, FR-050). */
export function FacturacionPage() {
  const consulta = useQuery(configuracionFacturacionQuery)
  const [ajustando, setAjustando] = useState(false)

  if (consulta.isError) {
    return (
      <ErrorState
        message="No se ha podido cargar la configuración de facturación."
        onRetry={() => void consulta.refetch()}
      />
    )
  }
  const config = consulta.data
  if (!config) {
    return (
      <div className="flex flex-col gap-5" aria-busy="true" aria-label="Cargando">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <AvisoEmision faltan={config.faltan} />
      <Card className="p-6">
        <Formulario key={config.version} config={config} />
      </Card>
      <Card className="flex flex-col gap-4 p-6 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-col gap-1">
          <span className="label-md text-primary">Numeración</span>
          <span className="body-md text-on-surface-variant">
            Próxima factura ordinaria de este año
          </span>
          <span className="headline-sm text-on-surface tabular-nums">{config.proximo_numero}</span>
        </div>
        <Button
          variant="secondary"
          onPress={() => {
            setAjustando(true)
          }}
        >
          Ajustar numeración
        </Button>
      </Card>
      <AjusteContadorDialog isOpen={ajustando} onOpenChange={setAjustando} />
    </div>
  )
}
