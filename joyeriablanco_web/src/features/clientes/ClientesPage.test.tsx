import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { delay, http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { conCatalogos, conSesion, crearCliente, crearSesion, renderApp } from '../../test/app'
import { server } from '../../test/msw'

function conListado(
  elementos: ReturnType<typeof crearCliente>[],
  total = elementos.length,
  espera = 0,
) {
  const recibidas: URLSearchParams[] = []
  server.use(
    http.get('*/api/v1/clientes', async ({ request }) => {
      recibidas.push(new URL(request.url).searchParams)
      if (espera) await delay(espera)
      return HttpResponse.json({ elementos, total, pagina: 1, tamano: 25 })
    }),
    http.get('*/api/v1/clientes/indicadores', () =>
      HttpResponse.json({ activos: 128, nuevos_este_anio: 24 }),
    ),
  )
  return recibidas
}

describe('ClientesPage', () => {
  it('muestra indicadores, listado y tipo de cada cliente', async () => {
    conSesion(crearSesion())
    conCatalogos()
    conListado([
      crearCliente(),
      crearCliente({ id: 'c2', nombre: 'Joyería Serrano', tipo: 'empresa', activo: false }),
    ])
    renderApp('/clientes')

    expect(await screen.findByText('128')).toBeInTheDocument()
    expect(screen.getByText('24')).toBeInTheDocument()
    const tabla = await screen.findByRole('table', { name: 'Listado de clientes' })
    expect(within(tabla).getByText('María López García')).toBeInTheDocument()
    expect(within(tabla).getByText('Empresa')).toBeInTheDocument()
    expect(within(tabla).getByText('Inactivo')).toBeInTheDocument()
    expect(within(tabla).queryByText('Facturas')).toBeNull() // FR-035
    const editar = within(tabla).getByRole('link', { name: 'Editar cliente María López García' })
    // El enlace conserva los filtros de la URL al abrir la ficha.
    expect(editar.getAttribute('href')).toMatch(new RegExp(`^/clientes/${crearCliente().id}\\?`))
  })

  it('muestra esqueletos mientras carga', async () => {
    conSesion(crearSesion())
    conCatalogos()
    conListado([crearCliente()], 1, 300)
    renderApp('/clientes')

    expect(await screen.findByLabelText('Cargando clientes')).toBeInTheDocument()
    const tabla = await screen.findByRole('table', {}, { timeout: 2000 })
    expect(within(tabla).getByText('María López García')).toBeInTheDocument()
  })

  it('distingue "todavía no hay clientes" de "no hay resultados"', async () => {
    conSesion(crearSesion())
    conCatalogos()
    conListado([], 0)
    const { unmount } = renderApp('/clientes')
    expect(await screen.findByText('Todavía no hay clientes')).toBeInTheDocument()
    unmount()

    renderApp('/clientes?q=zafiro')
    expect(await screen.findByText('No hay resultados')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Limpiar filtros' })).toBeInTheDocument()
  })

  it('muestra un error con opción de reintentar', async () => {
    conSesion(crearSesion())
    conCatalogos()
    let intentos = 0
    server.use(
      http.get('*/api/v1/clientes', () => {
        intentos += 1
        return intentos === 1
          ? HttpResponse.json(
              { type: '/problemas/interno', title: 'Error del servidor', status: 500 },
              { status: 500 },
            )
          : HttpResponse.json({ elementos: [crearCliente()], total: 1, pagina: 1, tamano: 25 })
      }),
      http.get('*/api/v1/clientes/indicadores', () =>
        HttpResponse.json({ activos: 1, nuevos_este_anio: 1 }),
      ),
    )
    // El QueryClient de pruebas no reintenta: el primer 500 muestra el error.
    renderApp('/clientes')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Reintentar' }))

    const tabla = await screen.findByRole('table')
    expect(within(tabla).getByText('María López García')).toBeInTheDocument()
  })

  it('la búsqueda y los filtros se reflejan en la URL y en la petición', async () => {
    conSesion(crearSesion())
    conCatalogos()
    const recibidas = conListado([crearCliente()])
    const { router } = renderApp('/clientes')
    const user = userEvent.setup()

    await user.type(await screen.findByPlaceholderText('Buscar nombre, NIF o localidad'), 'maria')

    await waitFor(() => {
      expect(router.state.location.search).toMatchObject({ q: 'maria', pagina: 1 })
    })
    await waitFor(() => {
      expect(recibidas.some((p) => p.get('q') === 'maria' && p.get('estado') === 'activos')).toBe(
        true,
      )
    })
  })

  it('en móvil presenta cada cliente como tarjeta', async () => {
    conSesion(crearSesion())
    conCatalogos()
    conListado([crearCliente()])
    renderApp('/clientes')

    const tarjetas = await screen.findByRole('list', { name: 'Listado de clientes' })
    expect(within(tarjetas).getByText('María López García')).toBeInTheDocument()
    expect(tarjetas.className).toContain('md:hidden')
  })
})
