import { screen, waitFor } from '@testing-library/react'
import { http } from 'msw'
import { describe, expect, it } from 'vitest'
import { api } from '../api/client'
import { conSesion, crearSesion, problema, renderApp } from '../test/app'
import { server } from '../test/msw'

describe('Pérdida de sesión (FR-004, FR-011)', () => {
  it('un 401 que llega ya en el acceso no repite el aviso ni cambia la vuelta', async () => {
    conSesion(crearSesion())
    const { router } = renderApp('/cuenta')
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/cuenta')
    })
    conSesion(null)
    server.use(
      http.get('*/api/v1/alarmas', () => problema(401, 'no-autenticado', 'Sesión no válida')),
    )

    await api.GET('/api/v1/alarmas')
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/acceso')
    })
    await waitFor(() => {
      expect(router.state.status).toBe('idle')
    })
    await new Promise((fin) => setTimeout(fin, 0)) // termina la navegación (`finally`)
    // La banda de alarma, aún montada al olvidar la caché, repite su consulta: llega tarde.
    await api.GET('/api/v1/alarmas')

    expect(
      await screen.findAllByText('Tu sesión ha caducado. Vuelve a identificarte.'),
    ).toHaveLength(1)
    expect(router.state.location.search).toEqual({ volver: '/cuenta' })
  })
})
