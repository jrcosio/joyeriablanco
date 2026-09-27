import { zodResolver } from '@hookform/resolvers/zod'
import { Link } from '@tanstack/react-router'
import { TriangleAlert } from 'lucide-react'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Controller, useForm, useWatch, type Control, type Path } from 'react-hook-form'
import { Form } from 'react-aria-components'
import { ApiError } from '../../api/client'
import type { CatalogosSalida, ClienteEntrada, ClienteSalida } from '../../api/tipos'
import {
  aCuerpo,
  CAMPOS,
  esquema,
  tiposPermitidos,
  valoresIniciales,
  type ValoresCliente,
} from './cliente-valores'
import { Alerta } from '../../components/forms/Alerta'
import { ComboBox } from '../../components/ui/ComboBox'
import { Select, type OpcionSelect } from '../../components/ui/Select'
import { TextField } from '../../components/ui/TextField'
import { opcionesPaises } from '../../lib/paises'

export interface ClienteExistente {
  id: string
  nombre: string
  activo: boolean
}

export interface ClienteFormProps {
  formId: string
  catalogos: CatalogosSalida
  cliente?: ClienteSalida
  onEnviar: (cuerpo: ClienteEntrada) => Promise<void>
  onConflicto?: () => void
  onDirtyChange?: (sucio: boolean) => void
  /** Acción adicional ante un duplicado (p. ej. reactivar un cliente inactivo, US4). */
  accionDuplicado?: (existente: ClienteExistente) => ReactNode
}

function Seccion({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <fieldset className="flex flex-col gap-5 border-t border-primary-container/18 pt-5 first:border-t-0 first:pt-0">
      <legend className="mb-4 label-md text-primary">{titulo}</legend>
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">{children}</div>
    </fieldset>
  )
}

function Campo({
  control,
  name,
  label,
  className,
  ...resto
}: {
  control: Control<ValoresCliente>
  name: Path<ValoresCliente>
  label: string
  className?: string
  isRequired?: boolean
  type?: string
  autoComplete?: string
  inputMode?: 'numeric' | 'tel' | 'email' | 'text'
  multiline?: boolean
  description?: string
}) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <TextField
          {...resto}
          label={label}
          value={field.value}
          onChange={field.onChange}
          onBlur={field.onBlur}
          error={fieldState.error?.message}
          className={className}
        />
      )}
    />
  )
}

/** Formulario de alta y edición de clientes (US2; FR-023 a FR-030, FR-055, FR-058). */
export function ClienteForm({
  formId,
  catalogos,
  cliente,
  onEnviar,
  onConflicto,
  onDirtyChange,
  accionDuplicado,
}: ClienteFormProps) {
  const [error, setError] = useState<string | null>(null)
  const [duplicado, setDuplicado] = useState<ClienteExistente | null>(null)
  const {
    control,
    handleSubmit,
    setValue,
    getValues,
    setError: marcarError,
    formState,
  } = useForm<ValoresCliente>({
    resolver: zodResolver(esquema),
    defaultValues: valoresIniciales(cliente),
  })

  useEffect(() => {
    onDirtyChange?.(formState.isDirty)
  }, [formState.isDirty, onDirtyChange])

  const paisId = useWatch({ control, name: 'identificacion_pais' })
  const paisResidencia = useWatch({ control, name: 'pais_residencia' })
  const codigoPostal = useWatch({ control, name: 'codigo_postal' })

  const paises = useMemo(
    () => opcionesPaises(catalogos.paises).map((p) => ({ id: p.codigo, label: p.nombre })),
    [catalogos.paises],
  )
  const provincias: OpcionSelect[] = useMemo(
    () => catalogos.provincias.map((p) => ({ id: p.codigo, label: p.nombre_visible })),
    [catalogos.provincias],
  )
  const opcionesTipoId: OpcionSelect[] = tiposPermitidos(paisId, catalogos).map((t) => ({
    id: t.codigo,
    label: t.descripcion,
  }))

  // El tipo de identificación debe ser coherente con el país (research R-20.1).
  useEffect(() => {
    const permitidos = tiposPermitidos(paisId, catalogos).map((t) => t.codigo)
    const actual = getValues('identificacion_tipo')
    const primero = permitidos[0]
    if (!permitidos.includes(actual) && primero) {
      setValue('identificacion_tipo', primero, { shouldDirty: true })
    }
  }, [paisId, catalogos, getValues, setValue])

  // Previsualización: la provincia se deduce del CP español (el servidor la vuelve a derivar).
  useEffect(() => {
    if (paisResidencia !== 'ES' || !/^\d{5}$/.test(codigoPostal)) return
    const prefijo = codigoPostal.slice(0, 2)
    if (catalogos.provincias.some((p) => p.codigo === prefijo)) {
      setValue('provincia_codigo', prefijo, { shouldDirty: true })
    }
  }, [codigoPostal, paisResidencia, catalogos.provincias, setValue])

  const enviar = handleSubmit(async (valores) => {
    setError(null)
    setDuplicado(null)
    try {
      await onEnviar(aCuerpo(valores))
    } catch (e) {
      if (!(e instanceof ApiError)) {
        setError('No se ha podido guardar el cliente.')
        return
      }
      if (e.tipo === 'validacion') {
        const sinCampo: string[] = []
        for (const [campo, mensaje] of Object.entries(e.porCampo)) {
          if ((CAMPOS as string[]).includes(campo)) {
            marcarError(campo as keyof ValoresCliente, { message: mensaje })
          } else {
            sinCampo.push(mensaje)
          }
        }
        setError(sinCampo.length ? sinCampo.join(' ') : 'Revisa los campos indicados.')
      } else if (e.tipo === 'duplicado') {
        setDuplicado(e.problema.cliente_existente as ClienteExistente)
      } else if (e.tipo === 'conflicto-version' && onConflicto) {
        onConflicto()
      } else {
        setError(e.message)
      }
    }
  })

  return (
    <Form
      id={formId}
      className="flex flex-col gap-6"
      validationBehavior="aria"
      onSubmit={(e) => {
        e.preventDefault()
        void enviar()
      }}
    >
      <Seccion titulo="Datos fiscales">
        <Controller
          control={control}
          name="tipo"
          render={({ field }) => (
            <Select
              label="Tipo de cliente"
              isRequired
              options={[
                { id: 'particular', label: 'Particular' },
                { id: 'empresa', label: 'Empresa' },
              ]}
              value={field.value}
              onChange={(v) => {
                if (v) field.onChange(v)
              }}
            />
          )}
        />
        <Campo control={control} name="nombre" label="Nombre o razón social" isRequired />
        <Controller
          control={control}
          name="identificacion_pais"
          render={({ field, fieldState }) => (
            <ComboBox
              label="País de la identificación"
              isRequired
              options={paises}
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
          name="identificacion_tipo"
          render={({ field, fieldState }) => (
            <Select
              label="Tipo de identificación"
              isRequired
              options={opcionesTipoId}
              value={field.value}
              onChange={(v) => {
                if (v) field.onChange(v)
              }}
              error={fieldState.error?.message}
            />
          )}
        />
        <Campo
          control={control}
          name="identificacion_numero"
          label="Número de identificación"
          isRequired
          autoComplete="off"
          className="md:col-span-2"
        />
      </Seccion>

      <Seccion titulo="Dirección">
        <Campo
          control={control}
          name="direccion"
          label="Dirección"
          autoComplete="street-address"
          className="md:col-span-2"
        />
        <Campo
          control={control}
          name="codigo_postal"
          label="Código postal"
          autoComplete="postal-code"
          inputMode={paisResidencia === 'ES' ? 'numeric' : 'text'}
        />
        <Campo control={control} name="localidad" label="Localidad" autoComplete="address-level2" />
        {paisResidencia === 'ES' ? (
          <Controller
            control={control}
            name="provincia_codigo"
            render={({ field, fieldState }) => (
              <Select
                label="Provincia"
                options={provincias}
                value={field.value || null}
                onChange={(v) => {
                  field.onChange(v ?? '')
                }}
                error={fieldState.error?.message}
              />
            )}
          />
        ) : (
          <Campo control={control} name="provincia_texto" label="Provincia o región" />
        )}
        <Controller
          control={control}
          name="pais_residencia"
          render={({ field, fieldState }) => (
            <ComboBox
              label="País de residencia"
              isRequired
              options={paises}
              value={field.value}
              onChange={(v) => {
                if (v) field.onChange(v)
              }}
              error={fieldState.error?.message}
            />
          )}
        />
      </Seccion>

      <Seccion titulo="Contacto">
        <Campo
          control={control}
          name="telefono"
          label="Teléfono"
          type="tel"
          autoComplete="tel"
          inputMode="tel"
        />
        <Campo
          control={control}
          name="correo"
          label="Correo electrónico"
          type="email"
          autoComplete="email"
          inputMode="email"
        />
        <Campo
          control={control}
          name="observaciones"
          label="Observaciones"
          multiline
          className="md:col-span-2"
        />
      </Seccion>

      {duplicado ? (
        <div
          role="alert"
          className="flex flex-col gap-3 border border-warning/40 bg-warning/8 px-4 py-3"
        >
          <p className="flex items-start gap-3 body-md text-on-surface">
            <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-warning" />
            <span>
              Ya existe un cliente con esta identificación: <strong>{duplicado.nombre}</strong>
              {duplicado.activo ? '.' : ' (inactivo).'}
            </span>
          </p>
          <div className="flex flex-wrap gap-4 pl-7">
            <Link
              to="/clientes/$clienteId"
              params={{ clienteId: duplicado.id }}
              className="label-lg text-primary underline-offset-4 hover:underline"
            >
              Ir al cliente
            </Link>
            {accionDuplicado?.(duplicado)}
          </div>
        </div>
      ) : null}
      <Alerta mensaje={error} />
    </Form>
  )
}
