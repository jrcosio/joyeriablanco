import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { conSesion, crearSesion, problema, renderApp } from '../../test/app'
import { server } from '../../test/msw'

async function rellenarYEnviar(usuario = 'ana.garcia', contrasena = 'una-contraseña-larga') {
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Usuario'), usuario)
  await user.type(screen.getByLabelText('Contraseña'), contrasena)
  await user.click(screen.getByRole('button', { name: 'Entrar' }))
}

describe('LoginPage', () => {
  it('muestra el mensaje genérico del servidor si las credenciales no son válidas', async () => {
    conSesion(null)
    server.use(
      http.post('*/api/v1/sesion', () =>
        problema(401, 'credenciales', 'Usuario o contraseña incorrectos.'),
      ),
    )
    renderApp('/acceso')

    await rellenarYEnviar()

    const mensaje = await screen.findByText('Usuario o contraseña incorrectos.')
    expect(mensaje.closest('[role="alert"]')).not.toBeNull()
  })

  it('muestra el mensaje propio del límite por origen', async () => {
    conSesion(null)
    server.use(
      http.post('*/api/v1/sesion', () =>
        problema(
          429,
          'limite-origen',
          'Demasiados intentos desde este equipo. Inténtalo de nuevo en unos minutos.',
        ),
      ),
    )
    renderApp('/acceso')

    await rellenarYEnviar()

    const mensaje = await screen.findByText(/Demasiados intentos desde este equipo/)
    expect(mensaje.closest('[role="alert"]')).not.toBeNull()
  })

  it('exige usuario y contraseña antes de enviar', async () => {
    conSesion(null)
    renderApp('/acceso')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Entrar' }))

    expect(await screen.findByText('Introduce tu usuario.')).toBeInTheDocument()
    expect(screen.getByText('Introduce tu contraseña.')).toBeInTheDocument()
  })

  it('tras acceder vuelve a la pantalla que se quería abrir', async () => {
    conSesion(null)
    const sesion = crearSesion()
    server.use(http.post('*/api/v1/sesion', () => HttpResponse.json(sesion)))
    const { router } = renderApp('/acceso?volver=%2Fcuenta')

    await rellenarYEnviar()

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/cuenta')
    })
  })

  it('con contraseña temporal lleva al cambio obligatorio', async () => {
    conSesion(null)
    const sesion = crearSesion({ contrasena_temporal: true })
    server.use(http.post('*/api/v1/sesion', () => HttpResponse.json(sesion)))
    const { router } = renderApp('/acceso')

    await rellenarYEnviar()

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/cambiar-contrasena')
    })
    expect(await screen.findByText('Cambia tu contraseña')).toBeInTheDocument()
  })

  it('sin sesión, una ruta protegida redirige al acceso conservando la ruta', async () => {
    conSesion(null)
    const { router } = renderApp('/cuenta')

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/acceso')
    })
    expect(router.state.location.search).toEqual({ volver: '/cuenta' })
  })
})
