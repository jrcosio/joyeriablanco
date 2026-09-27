import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import {
  conCatalogos,
  conSesion,
  crearCliente,
  crearSesion,
  problema,
  renderApp,
} from '../../test/app'
import { server } from '../../test/msw'

async function rellenarMinimo(nombre = 'Carlos Martín Ruiz', nif = '45678901G') {
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText(/Nombre o razón social/), nombre)
  await user.type(screen.getByLabelText(/Número de identificación/), nif)
  return user
}

describe('ClienteForm', () => {
  it('con país España solo ofrece NIF y pasaporte', async () => {
    conSesion(crearSesion())
    conCatalogos()
    renderApp('/clientes/nuevo')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /Tipo de identificación/ }))

    const opciones = within(await screen.findByRole('listbox')).getAllByRole('option')
    expect(opciones.map((o) => o.textContent)).toEqual([
      'NIF (DNI, NIE o NIF de entidad)',
      'Pasaporte',
    ])
  })

  it('muestra los errores del servidor junto a su campo', async () => {
    conSesion(crearSesion())
    conCatalogos()
    server.use(
      http.post('*/api/v1/clientes', () =>
        HttpResponse.json(
          {
            type: '/problemas/validacion',
            title: 'Datos no válidos',
            status: 422,
            errores: [
              { campo: 'identificacion_numero', mensaje: 'La letra del NIF no es correcta.' },
            ],
          },
          { status: 422 },
        ),
      ),
    )
    renderApp('/clientes/nuevo')

    const user = await rellenarMinimo('Carlos Martín Ruiz', '45678901X')
    await user.click(screen.getByRole('button', { name: 'Crear cliente' }))

    const campo = screen.getByLabelText(/Número de identificación/)
    await waitFor(() => {
      expect(campo).toHaveAttribute('aria-invalid', 'true')
    })
    expect(screen.getByText('La letra del NIF no es correcta.')).toBeInTheDocument()
  })

  it('crea el cliente y vuelve al listado con un aviso', async () => {
    conSesion(crearSesion())
    conCatalogos()
    let recibido: Record<string, unknown> = {}
    server.use(
      http.post('*/api/v1/clientes', async ({ request }) => {
        recibido = (await request.json()) as Record<string, unknown>
        return HttpResponse.json(crearCliente({ nombre: 'Carlos Martín Ruiz' }), { status: 201 })
      }),
    )
    const { router } = renderApp('/clientes/nuevo')

    const user = await rellenarMinimo()
    await user.click(screen.getByRole('button', { name: 'Crear cliente' }))

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/clientes')
    })
    expect(await screen.findByText('Cliente «Carlos Martín Ruiz» creado.')).toBeInTheDocument()
    expect(recibido).toMatchObject({
      tipo: 'particular',
      identificacion_pais: 'ES',
      identificacion_tipo: 'NIF',
      identificacion_numero: '45678901G',
      correo: null,
    })
  })

  it('ante un duplicado enlaza con el cliente existente', async () => {
    conSesion(crearSesion())
    conCatalogos()
    server.use(
      http.post('*/api/v1/clientes', () =>
        HttpResponse.json(
          {
            type: '/problemas/duplicado',
            title: 'Ya existe',
            status: 409,
            detail: 'Ya existe un cliente con esta identificación.',
            cliente_existente: { id: 'abc', nombre: 'Carlos Martín Ruiz', activo: false },
          },
          { status: 409 },
        ),
      ),
    )
    renderApp('/clientes/nuevo')

    const user = await rellenarMinimo()
    await user.click(screen.getByRole('button', { name: 'Crear cliente' }))

    expect(
      await screen.findByText(/Ya existe un cliente con esta identificación/),
    ).toBeInTheDocument()
    expect(screen.getByText(/\(inactivo\)/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ir al cliente' })).toHaveAttribute(
      'href',
      '/clientes/abc',
    )
  })

  it('avisa antes de descartar cambios sin guardar', async () => {
    conSesion(crearSesion())
    conCatalogos()
    renderApp('/clientes/nuevo')

    const user = await rellenarMinimo()
    await user.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(
      await screen.findByRole('alertdialog', { name: '¿Descartar los cambios?' }),
    ).toBeInTheDocument()
  })

  it('ante un conflicto de versión ofrece recargar o seguir editando', async () => {
    const cliente = crearCliente()
    conSesion(crearSesion())
    conCatalogos()
    server.use(
      http.get('*/api/v1/clientes/:id', () => HttpResponse.json(cliente)),
      http.put('*/api/v1/clientes/:id', () =>
        problema(409, 'conflicto-version', 'El cliente ha cambiado desde que lo abriste.'),
      ),
    )
    renderApp(`/clientes/${cliente.id}`)
    const user = userEvent.setup()

    const localidad = await screen.findByLabelText('Localidad')
    await user.clear(localidad)
    await user.type(localidad, 'Ronda')
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    const dialogo = await screen.findByRole('alertdialog', { name: 'El cliente ha cambiado' })
    expect(within(dialogo).getByRole('button', { name: 'Recargar datos' })).toBeInTheDocument()
    expect(within(dialogo).getByRole('button', { name: 'Seguir editando' })).toBeInTheDocument()
  })

  it('muestra la trazabilidad del cliente', async () => {
    const cliente = crearCliente()
    conSesion(crearSesion())
    conCatalogos()
    server.use(http.get('*/api/v1/clientes/:id', () => HttpResponse.json(cliente)))
    renderApp(`/clientes/${cliente.id}`)

    expect(await screen.findByText('Trazabilidad')).toBeInTheDocument()
    // creado y última modificación: 10:00 UTC = 12:00 en Madrid (horario de verano)
    expect(screen.getAllByText('27/05/2026, 12:00 · Ana García')).toHaveLength(2)
  })
})
