import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { Form } from 'react-aria-components'
import { z } from 'zod'
import { ApiError } from '../../api/client'
import { iniciarSesion, rutaSegura } from '../../auth/session'
import { Alerta } from '../../components/forms/Alerta'
import { Marca } from '../../components/layout/Marca'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { TextField } from '../../components/ui/TextField'

const esquema = z.object({
  nombre_usuario: z.string().trim().min(1, 'Introduce tu usuario.'),
  contrasena: z.string().min(1, 'Introduce tu contraseña.'),
})
type Credenciales = z.infer<typeof esquema>

/** Pantalla de acceso (US1). Mensajes genéricos del servidor (FR-007). */
export function LoginPage({ volver }: { volver?: string | undefined }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const { control, handleSubmit, formState } = useForm<Credenciales>({
    resolver: zodResolver(esquema),
    defaultValues: { nombre_usuario: '', contrasena: '' },
  })

  const enviar = handleSubmit(async (datos) => {
    setError(null)
    try {
      const sesion = await iniciarSesion(queryClient, datos)
      if (sesion.usuario.contrasena_temporal) {
        await navigate({ to: '/cambiar-contrasena' })
      } else {
        await navigate({ href: rutaSegura(volver) })
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se ha podido iniciar sesión.')
    }
  })

  return (
    <main className="flex min-h-dvh items-center justify-center px-4 py-10">
      <Card className="flex w-full max-w-md flex-col gap-8 px-6 py-10 sm:px-10">
        <Marca tamano="lg" />
        <div className="flex flex-col gap-1 text-center">
          <h1 className="headline-md text-on-surface">Acceso</h1>
          <p className="body-md text-on-surface-variant">Gestión de facturación</p>
        </div>
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
            name="nombre_usuario"
            render={({ field, fieldState }) => (
              <TextField
                label="Usuario"
                autoComplete="username"
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
            name="contrasena"
            render={({ field, fieldState }) => (
              <TextField
                label="Contraseña"
                type="password"
                autoComplete="current-password"
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
                error={fieldState.error?.message}
              />
            )}
          />
          <Alerta mensaje={error} />
          <Button type="submit" isDisabled={formState.isSubmitting} className="mt-2 w-full">
            {formState.isSubmitting ? 'Entrando…' : 'Entrar'}
          </Button>
        </Form>
      </Card>
    </main>
  )
}
