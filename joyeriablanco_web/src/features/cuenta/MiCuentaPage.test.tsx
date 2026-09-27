import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { conSesion, crearSesion, renderApp } from '../../test/app'
import { server } from '../../test/msw'

async function rellenar(actual: string, nueva: string, repetida = nueva) {
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Contraseña actual'), actual)
  await user.type(screen.getByLabelText('Contraseña nueva'), nueva)
  await user.type(screen.getByLabelText('Repite la contraseña nueva'), repetida)
  await user.click(screen.getByRole('button', { name: 'Cambiar contraseña' }))
}

describe('Mi cuenta (US6)', () => {
  it('cambia la contraseña y avisa de que se cierran las demás sesiones', async () => {
    conSesion(crearSesion())
    let cuerpo: unknown = null
    server.use(
      http.put('*/api/v1/cuenta/contrasena', async ({ request }) => {
        cuerpo = await request.json()
        return new HttpResponse(null, { status: 204 })
      }),
    )
    renderApp('/cuenta')

    await rellenar('actual-larga-123', 'Zafiro-Topacio-Granate-77')

    expect(
      await screen.findByText('Contraseña actualizada. Se han cerrado tus otras sesiones.'),
    ).toBeInTheDocument()
    expect(cuerpo).toEqual({
      contrasena_actual: 'actual-larga-123',
      contrasena_nueva: 'Zafiro-Topacio-Granate-77',
    })
  })

  it('comprueba que la confirmación coincide antes de enviar', async () => {
    conSesion(crearSesion())
    renderApp('/cuenta')

    await rellenar('actual-larga-123', 'Zafiro-Topacio-Granate-77', 'otra-cosa-distinta')

    expect(await screen.findByText('Las contraseñas no coinciden.')).toBeInTheDocument()
  })

  it('muestra el motivo de rechazo de la política junto al campo', async () => {
    conSesion(crearSesion())
    server.use(
      http.put('*/api/v1/cuenta/contrasena', () =>
        HttpResponse.json(
          {
            type: '/problemas/validacion',
            title: 'Datos no válidos',
            status: 422,
            errores: [
              {
                campo: 'contrasena_nueva',
                mensaje: 'Es una contraseña demasiado común. Elige otra.',
              },
            ],
          },
          { status: 422 },
        ),
      ),
    )
    renderApp('/cuenta')

    await rellenar('actual-larga-123', 'qwertyuiopasdfghjkl')

    expect(
      await screen.findByText('Es una contraseña demasiado común. Elige otra.'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Contraseña nueva')).toHaveAttribute('aria-invalid', 'true')
  })
})
