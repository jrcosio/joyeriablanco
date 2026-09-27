import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { conSesion, crearSesion, renderApp } from '../../test/app'
import { server } from '../../test/msw'

describe('UserMenu', () => {
  it('muestra las iniciales y, al abrirlo, nombre, rol y opciones', async () => {
    conSesion(crearSesion({ nombre: 'Luis Martín', rol: 'administrador' }))
    renderApp('/clientes')
    const user = userEvent.setup()

    const boton = await screen.findByRole('button', { name: 'Menú de Luis Martín' })
    expect(boton).toHaveTextContent('LM')
    await user.click(boton)

    expect(await screen.findByText('Administrador')).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Mi cuenta' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Cerrar sesión' })).toBeInTheDocument()
  })

  it('cerrar sesión invalida la sesión en el servidor con CSRF y vuelve al acceso', async () => {
    const sesion = crearSesion()
    let cerrada = false
    let csrfRecibido: string | null = null
    server.use(
      http.get('*/api/v1/sesion', () =>
        cerrada
          ? HttpResponse.json(
              { type: '/problemas/no-autenticado', title: 'x', status: 401 },
              { status: 401 },
            )
          : HttpResponse.json(sesion),
      ),
      http.delete('*/api/v1/sesion', ({ request }) => {
        cerrada = true
        csrfRecibido = request.headers.get('X-CSRF-Token')
        return new HttpResponse(null, { status: 204 })
      }),
    )
    const { router } = renderApp('/clientes')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Menú de Ana García' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Cerrar sesión' }))

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/acceso')
    })
    expect(csrfRecibido).toBe('csrf-de-prueba')
  })

  it('la fecha de la cabecera aparece en formato largo en español', async () => {
    conSesion(crearSesion())
    renderApp('/clientes')

    const fecha = await screen.findByText(/^[A-ZÁÉÍÓÚ][a-záéíóú]+, \d{1,2} de [a-z]+ de \d{4}$/)
    expect(fecha.tagName).toBe('TIME')
  })
})
