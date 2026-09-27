import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { conCatalogos, conSesion, crearCliente, crearSesion, renderApp } from '../../test/app'
import { server } from '../../test/msw'

function conCliente(cliente: ReturnType<typeof crearCliente>) {
  const llamadas: string[] = []
  server.use(
    http.get('*/api/v1/clientes/:id', () => HttpResponse.json(cliente)),
    http.post('*/api/v1/clientes/:id/desactivacion', () => {
      llamadas.push('desactivacion')
      return HttpResponse.json({ ...cliente, activo: false })
    }),
    http.post('*/api/v1/clientes/:id/reactivacion', () => {
      llamadas.push('reactivacion')
      return HttpResponse.json({ ...cliente, activo: true })
    }),
    http.delete('*/api/v1/clientes/:id', () => {
      llamadas.push('borrado')
      return new HttpResponse(null, { status: 204 })
    }),
  )
  return llamadas
}

describe('Acciones del cliente (US4)', () => {
  it('pide confirmación antes de desactivar', async () => {
    const cliente = crearCliente()
    conSesion(crearSesion())
    conCatalogos()
    const llamadas = conCliente(cliente)
    renderApp(`/clientes/${cliente.id}`)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Desactivar cliente' }))
    const dialogo = await screen.findByRole('alertdialog', {
      name: '¿Desactivar a María López García?',
    })
    expect(llamadas).toEqual([])
    await user.click(within(dialogo).getByRole('button', { name: 'Desactivar' }))

    expect(await screen.findByText('Cliente desactivado.')).toBeInTheDocument()
    expect(llamadas).toEqual(['desactivacion'])
  })

  it('un cliente inactivo se puede reactivar', async () => {
    const cliente = crearCliente({ activo: false })
    conSesion(crearSesion())
    conCatalogos()
    const llamadas = conCliente(cliente)
    renderApp(`/clientes/${cliente.id}`)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Reactivar cliente' }))

    expect(await screen.findByText('Cliente reactivado.')).toBeInTheDocument()
    expect(llamadas).toEqual(['reactivacion'])
  })

  it('un empleado no ve la opción de borrar', async () => {
    const cliente = crearCliente()
    conSesion(crearSesion({ rol: 'empleado' }))
    conCatalogos()
    conCliente(cliente)
    renderApp(`/clientes/${cliente.id}`)

    await screen.findByRole('button', { name: 'Desactivar cliente' })
    expect(screen.queryByRole('button', { name: 'Borrar definitivamente' })).toBeNull()
  })

  it('el borrado exige escribir la identificación del cliente', async () => {
    const cliente = crearCliente()
    conSesion(crearSesion({ rol: 'administrador' }))
    conCatalogos()
    const llamadas = conCliente(cliente)
    const { router } = renderApp(`/clientes/${cliente.id}`)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Borrar definitivamente' }))
    const dialogo = await screen.findByRole('alertdialog', { name: 'Borrar definitivamente' })
    const borrar = within(dialogo).getByRole('button', { name: 'Borrar' })
    expect(borrar).toBeDisabled()

    await user.type(within(dialogo).getByLabelText(/Escribe la identificación/), '12345678-z')
    expect(borrar).toBeEnabled()
    await user.click(borrar)

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/clientes')
    })
    expect(llamadas).toEqual(['borrado'])
    expect(await screen.findByText('Cliente borrado.')).toBeInTheDocument()
  })
})
