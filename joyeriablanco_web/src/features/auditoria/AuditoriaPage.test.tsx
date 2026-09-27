import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { conSesion, crearSesion, renderApp } from '../../test/app'
import { server } from '../../test/msw'

const admin = crearSesion({ rol: 'administrador' })
const EVENTO = {
  id: 'e1',
  ocurrido_en: '2026-05-27T12:32:00Z',
  tipo: 'cliente_editado',
  actor: { id: 'u1', nombre: 'Lucía Moreno', eliminado: false },
  actor_nombre_usuario: 'lucia.moreno',
  origen_ip: '10.1.1.1',
  agente: 'Firefox',
  usuario_afectado: null,
  cliente_id: '0192f0c0-0000-7000-8000-00000000c001',
  detalle: { cambios: { localidad: ['Málaga', 'Ronda'] } },
}

describe('AuditoriaPage (US5)', () => {
  it('lista eventos, filtra por tipo y muestra el detalle de los cambios', async () => {
    conSesion(admin)
    const recibidas: URLSearchParams[] = []
    server.use(
      http.get('*/api/v1/usuarios', () => HttpResponse.json([admin.usuario])),
      http.get('*/api/v1/auditoria', ({ request }) => {
        recibidas.push(new URL(request.url).searchParams)
        return HttpResponse.json({ elementos: [EVENTO], total: 1, pagina: 1, tamano: 25 })
      }),
    )
    const { router } = renderApp('/configuracion/auditoria')
    const user = userEvent.setup()

    const tabla = await screen.findByRole('table', { name: 'Eventos de auditoría' })
    expect(within(tabla).getByText('Cliente editado')).toBeInTheDocument()
    expect(within(tabla).getByText('27/05/2026, 14:32')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Tipo de evento/ }))
    await user.click(await screen.findByRole('option', { name: 'Acceso fallido' }))
    await waitFor(() => {
      expect(router.state.location.search).toMatchObject({ tipo: 'acceso_fallido' })
    })
    await waitFor(() => {
      expect(recibidas.some((p) => p.get('tipo') === 'acceso_fallido')).toBe(true)
    })

    await user.click(within(tabla).getByRole('button', { name: /Ver detalle/ }))
    const detalle = await screen.findByRole('dialog')
    expect(within(detalle).getByText('localidad')).toBeInTheDocument()
    expect(within(detalle).getByText('Málaga')).toBeInTheDocument()
    expect(within(detalle).getByText('Ronda')).toBeInTheDocument()
  })

  it('marca a los usuarios eliminados en la tabla y en el filtro de usuario', async () => {
    conSesion(admin)
    const eliminada = {
      ...admin.usuario,
      id: 'u1',
      nombre: 'Lucía Moreno',
      nombre_usuario: 'lucia.moreno',
      activo: false,
      eliminado: true,
    }
    server.use(
      http.get('*/api/v1/usuarios', ({ request }) =>
        HttpResponse.json(
          new URL(request.url).searchParams.get('incluir_eliminados') === 'true'
            ? [admin.usuario, eliminada]
            : [admin.usuario],
        ),
      ),
      http.get('*/api/v1/auditoria', () =>
        HttpResponse.json({
          elementos: [
            {
              ...EVENTO,
              tipo: 'usuario_eliminado',
              actor: { id: admin.usuario.id, nombre: admin.usuario.nombre, eliminado: false },
              usuario_afectado: { id: 'u1', nombre: 'Lucía Moreno', eliminado: true },
              cliente_id: null,
              detalle: { nombre_usuario: 'lucia.moreno', nombre: 'Lucía Moreno', rol: 'empleado' },
            },
          ],
          total: 1,
          pagina: 1,
          tamano: 25,
        }),
      ),
    )
    renderApp('/configuracion/auditoria')
    const user = userEvent.setup()

    const tabla = await screen.findByRole('table', { name: 'Eventos de auditoría' })
    expect(within(tabla).getByText('Usuario eliminado')).toBeInTheDocument()
    expect(within(tabla).getByText('Lucía Moreno (eliminado)')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Todos los usuarios/ }))
    expect(
      await screen.findByRole('option', { name: 'Lucía Moreno (eliminado)' }),
    ).toBeInTheDocument()
  })

  it('el filtro por fechas envía los límites del día en hora peninsular', async () => {
    conSesion(admin)
    const recibidas: URLSearchParams[] = []
    server.use(
      http.get('*/api/v1/usuarios', () => HttpResponse.json([admin.usuario])),
      http.get('*/api/v1/auditoria', ({ request }) => {
        recibidas.push(new URL(request.url).searchParams)
        return HttpResponse.json({ elementos: [], total: 0, pagina: 1, tamano: 25 })
      }),
    )
    renderApp('/configuracion/auditoria?desde=2026-07-01&hasta=2026-07-31')

    expect(await screen.findByText('No hay eventos')).toBeInTheDocument()
    const ultima = recibidas.at(-1)
    expect(ultima?.get('desde')).toBe('2026-07-01T00:00:00+02:00')
    expect(ultima?.get('hasta')).toBe('2026-07-31T23:59:59.999+02:00')
  })
})
