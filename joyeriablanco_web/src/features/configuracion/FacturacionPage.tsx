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
import { ErrorState } from '../../components/ui/ErrorState'
import { Select } from '../../components/ui/Select'
import { Skeleton } from '../../components/ui/Skeleton'
import { TextField } from '../../components/ui/TextField'
import { toast } from '../../components/ui/toast-store'
import { CLAVES_REGIMEN, MODALIDADES, textoFalta, textoTipoIva } from '../../lib/facturacion'
import { AjusteContadorDialog } from './AjusteContadorDialog'

const esquema = z.object({
  iva_por_defecto: z.string().min(1, 'Campo obligatorio.'),
  clave_regimen: z.string().regex(/^\d{2}$/, 'Campo obligatorio.'),
  modalidad: z.enum(['', 'verifactu', 'no_verifactu']),
  nombre: z.string().max(120),
  nif: z.string().max(20),
  direccion: z.string().max(200),
  codigo_postal: z.string().max(10),
  localidad: z.string().max(100),
})
type Valores = z.infer<typeof esquema>
type CampoFormulario = keyof Valores

const CAMPO_DEL_SERVIDOR: Record<string, CampoFormulario> = {
  iva_por_defecto: 'iva_por_defecto',
  clave_regimen: 'clave_regimen',
  modalidad: 'modalidad',
  'emisor.nombre': 'nombre',
  'emisor.nif': 'nif',
  'emisor.direccion': 'direccion',
  'emisor.codigo_postal': 'codigo_postal',
  'emisor.localidad': 'localidad',
}

function valoresIniciales(config: ConfiguracionFacturacionSalida): Valores {
  return {
    iva_por_defecto: config.iva_por_defecto,
    clave_regimen: config.clave_regimen,
    modalidad: config.modalidad ?? '',
    nombre: config.emisor.nombre ?? '',
    nif: config.emisor.nif ?? '',
    direccion: config.emisor.direccion ?? '',
    codigo_postal: config.emisor.codigo_postal ?? '',
    localidad: config.emisor.localidad ?? '',
  }
}

const vacioANulo = (valor: string) => (valor.trim() === '' ? null : valor.trim())

function aCuerpo(valores: Valores, version: number): ConfiguracionFacturacionEntrada {
  return {
    version,
    iva_por_defecto: valores.iva_por_defecto,
    clave_regimen: valores.clave_regimen,
    modalidad: valores.modalidad === '' ? null : valores.modalidad,
    emisor: {
      nombre: vacioANulo(valores.nombre),
      nif: vacioANulo(valores.nif),
      direccion: vacioANulo(valores.direccion),
      codigo_postal: vacioANulo(valores.codigo_postal),
      localidad: vacioANulo(valores.localidad),
    },
  }
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
  const {
    control,
    handleSubmit,
    setError: marcar,
  } = useForm<Valores>({
    resolver: zodResolver(esquema),
    defaultValues: valoresIniciales(config),
  })

  const enviar = handleSubmit(async (valores) => {
    setError(null)
    try {
      await guardar.mutateAsync(aCuerpo(valores, config.version))
      toast('Configuración de facturación guardada')
    } catch (e) {
      if (e instanceof ApiError && e.tipo === 'validacion' && e.problema.errores?.length) {
        for (const [campo, mensaje] of Object.entries(e.porCampo)) {
          const destino = CAMPO_DEL_SERVIDOR[campo]
          if (destino) marcar(destino, { message: mensaje })
          else setError(mensaje)
        }
      } else if (e instanceof ApiError && e.tipo === 'tipo-iva-no-admitido') {
        marcar('iva_por_defecto', { message: e.message })
      } else {
        setError(e instanceof ApiError ? e.message : 'No se ha podido guardar la configuración.')
      }
    }
  })

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
              <Select
                label="IVA por defecto"
                isRequired
                options={config.tipos_iva_admitidos.map((t) => ({ id: t, label: textoTipoIva(t) }))}
                value={field.value}
                onChange={(v) => {
                  if (v) field.onChange(v)
                }}
                error={fieldState.error?.message}
              />
            )}
          />
          <Controller
            control={control}
            name="clave_regimen"
            render={({ field, fieldState }) => (
              <Select
                label="Clave de régimen del IVA"
                isRequired
                options={CLAVES_REGIMEN}
                value={field.value}
                onChange={(v) => {
                  if (v) field.onChange(v)
                }}
                error={fieldState.error?.message}
                className="md:col-span-2"
              />
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
          El IVA se aplica a todas las líneas de las facturas nuevas. Cambiarlo no altera las ya
          emitidas.
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
        </div>
      </fieldset>

      <Alerta mensaje={error} />
      <div className="flex justify-end">
        <Button type="submit" isDisabled={guardar.isPending}>
          {guardar.isPending ? 'Guardando…' : 'Guardar configuración'}
        </Button>
      </div>
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
