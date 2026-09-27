import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Controller, useForm, type Path } from 'react-hook-form'
import { Form } from 'react-aria-components'
import { z } from 'zod'
import { api, ApiError, unwrap } from '../../api/client'
import { SESION_KEY } from '../../auth/session'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { TextField } from '../../components/ui/TextField'

const esquema = z
  .object({
    contrasena_actual: z.string().min(1, 'Introduce tu contraseña actual.'),
    contrasena_nueva: z
      .string()
      .min(12, 'Debe tener al menos 12 caracteres.')
      .max(128, 'No puede superar 128 caracteres.'),
    confirmacion: z.string(),
  })
  .refine((d) => d.contrasena_nueva === d.confirmacion, {
    path: ['confirmacion'],
    message: 'Las contraseñas no coinciden.',
  })
type Datos = z.infer<typeof esquema>

const CAMPOS: readonly { name: Path<Datos>; label: string; auto: string }[] = [
  { name: 'contrasena_actual', label: 'Contraseña actual', auto: 'current-password' },
  { name: 'contrasena_nueva', label: 'Contraseña nueva', auto: 'new-password' },
  { name: 'confirmacion', label: 'Repite la contraseña nueva', auto: 'new-password' },
]

/**
 * Cambio de contraseña (FR-009, FR-019). La política la valida el servidor; aquí solo se
 * comprueba la forma y que la confirmación coincida.
 */
export function CambioContrasenaForm({ onHecho }: { onHecho: () => void }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const {
    control,
    handleSubmit,
    setError: marcarError,
    reset,
    formState,
  } = useForm<Datos>({
    resolver: zodResolver(esquema),
    defaultValues: { contrasena_actual: '', contrasena_nueva: '', confirmacion: '' },
  })

  const enviar = handleSubmit(async (datos) => {
    setError(null)
    try {
      await unwrap(
        api.PUT('/api/v1/cuenta/contrasena', {
          body: {
            contrasena_actual: datos.contrasena_actual,
            contrasena_nueva: datos.contrasena_nueva,
          },
        }),
      )
      await queryClient.invalidateQueries({ queryKey: SESION_KEY })
      reset()
      onHecho()
    } catch (e) {
      if (e instanceof ApiError && e.tipo === 'validacion') {
        for (const [campo, mensaje] of Object.entries(e.porCampo)) {
          if (campo === 'contrasena_actual' || campo === 'contrasena_nueva') {
            marcarError(campo, { message: mensaje })
          }
        }
      } else {
        setError(e instanceof ApiError ? e.message : 'No se ha podido cambiar la contraseña.')
      }
    }
  })

  return (
    <Form
      className="flex flex-col gap-5"
      validationBehavior="aria"
      onSubmit={(e) => {
        e.preventDefault()
        void enviar()
      }}
    >
      {CAMPOS.map((campo) => (
        <Controller
          key={campo.name}
          control={control}
          name={campo.name}
          render={({ field, fieldState }) => (
            <TextField
              label={campo.label}
              type="password"
              autoComplete={campo.auto}
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
              error={fieldState.error?.message}
              {...(campo.name === 'contrasena_nueva'
                ? {
                    description:
                      'Mínimo 12 caracteres. Puede ser una frase; evita contraseñas comunes.',
                  }
                : {})}
            />
          )}
        />
      ))}
      <Alerta mensaje={error} />
      <Button type="submit" isDisabled={formState.isSubmitting} className="self-start">
        {formState.isSubmitting ? 'Guardando…' : 'Cambiar contraseña'}
      </Button>
    </Form>
  )
}
