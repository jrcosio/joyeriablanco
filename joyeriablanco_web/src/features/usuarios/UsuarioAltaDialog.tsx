import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { Form } from 'react-aria-components'
import { z } from 'zod'
import { ApiError } from '../../api/client'
import { useCrearUsuario } from '../../api/queries/usuarios'
import type { UsuarioConContrasenaTemporal } from '../../api/tipos'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { Select } from '../../components/ui/Select'
import { TextField } from '../../components/ui/TextField'

const esquema = z.object({
  nombre: z.string().trim().min(1, 'Campo obligatorio.').max(120),
  nombre_usuario: z
    .string()
    .trim()
    .regex(/^[a-zA-Z0-9._-]{3,50}$/, 'De 3 a 50 caracteres: letras sin tildes, números, . - _'),
  rol: z.enum(['empleado', 'administrador']),
})
type Datos = z.infer<typeof esquema>

/** Alta de usuario (FR-014). La contraseña temporal la genera el servidor (FR-015). */
export function UsuarioAltaDialog({
  isOpen,
  onOpenChange,
  onCreado,
}: {
  isOpen: boolean
  onOpenChange: (abierto: boolean) => void
  onCreado: (resultado: UsuarioConContrasenaTemporal) => void
}) {
  const crear = useCrearUsuario()
  const [error, setError] = useState<string | null>(null)
  const {
    control,
    handleSubmit,
    reset,
    setError: marcar,
  } = useForm<Datos>({
    resolver: zodResolver(esquema),
    defaultValues: { nombre: '', nombre_usuario: '', rol: 'empleado' },
  })

  const enviar = handleSubmit(async (datos) => {
    setError(null)
    try {
      const resultado = await crear.mutateAsync(datos)
      reset()
      onCreado(resultado)
    } catch (e) {
      if (e instanceof ApiError && e.tipo === 'validacion') {
        for (const [campo, mensaje] of Object.entries(e.porCampo)) {
          if (campo === 'nombre' || campo === 'nombre_usuario' || campo === 'rol') {
            marcar(campo, { message: mensaje })
          }
        }
      } else {
        setError(e instanceof ApiError ? e.message : 'No se ha podido crear el usuario.')
      }
    }
  })

  return (
    <Dialog title="Nuevo usuario" isOpen={isOpen} onOpenChange={onOpenChange}>
      <Form
        className="flex flex-col gap-5"
        validationBehavior="aria"
        onSubmit={(e) => {
          e.preventDefault()
          void enviar()
        }}
      >
        <Controller
          control={control}
          name="nombre"
          render={({ field, fieldState }) => (
            <TextField
              label="Nombre"
              isRequired
              autoFocus
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
              error={fieldState.error?.message}
            />
          )}
        />
        <Controller
          control={control}
          name="nombre_usuario"
          render={({ field, fieldState }) => (
            <TextField
              label="Nombre de usuario"
              isRequired
              autoComplete="off"
              description="Con él se identificará al entrar (p. ej. lucia.moreno)."
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
              error={fieldState.error?.message}
            />
          )}
        />
        <Controller
          control={control}
          name="rol"
          render={({ field }) => (
            <Select
              label="Rol"
              isRequired
              options={[
                { id: 'empleado', label: 'Empleado' },
                { id: 'administrador', label: 'Administrador' },
              ]}
              value={field.value}
              onChange={(v) => {
                if (v === 'empleado' || v === 'administrador') field.onChange(v)
              }}
            />
          )}
        />
        <Alerta mensaje={error} />
        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            variant="secondary"
            onPress={() => {
              onOpenChange(false)
            }}
          >
            Cancelar
          </Button>
          <Button type="submit" isDisabled={crear.isPending}>
            Crear usuario
          </Button>
        </div>
      </Form>
    </Dialog>
  )
}
