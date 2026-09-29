import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import type { FacturaResumenSalida } from '../../api/tipos'
import { anioEnCurso } from '../../lib/fechas'
import { conSesion, crearSesion, renderApp } from '../../test/app'
import { server } from '../../test/msw'

function fila(parcial: Partial<FacturaResumenSalida> = {}): FacturaResumenSalida {
  return {
    tipo_documento: 'factura',
    id: '0192f0c0-0000-7000-8000-0000000f0001',
    num_serie: 'FAC-2026-0005',
    fecha: '2026-09-29',
    cliente_nombre: 'María López García',
    identificacion: '12345678Z',
    base: '1290.00',
    cuota: '270.90',
    total: '1560.90',
    estado: 'vigente',
    ...parcial,
  }
}

function conListado(elementos: FacturaResumenSalida[], total = elementos.length) {
  const recibidas: URLSearchParams[] = []
  server.use(
    http.get('*/api/v1/facturas', ({ request }) => {
      recibidas.push(new URL(request.url).searchParams)
      return HttpResponse.json({ elementos, total, pagina: 1, tamano: 25 })
    }),
  )
  return recibidas
}

describe('Listado de facturas (US3)', () => {
  it('muestra las columnas de FR-033, sin indicadores ni columna de estado', async () => {
    conSesion(crearSesion())
    conListado([fila()])
    renderApp('/facturas')

    const tabla = await screen.findByRole('table', { name: 'Listado de facturas' })
    const cabeceras = within(tabla)
      .getAllByRole('columnheader')
      .map((c) => c.textContent)
    expect(cabeceras).toEqual([
      'Número',
      'Fecha',
      'Cliente',
      'NIF/CIF',
      'Base imponible',
      'IVA',
      'Total',
      'Acciones',
    ])
    await within(tabla).findByText('FAC-2026-0005')
    expect(within(tabla).getByText('29/09/2026')).toBeInTheDocument()
    expect(within(tabla).getByText('1.290,00 €')).toBeInTheDocument()
    expect(within(tabla).getByText('270,90 €')).toBeInTheDocument()
    expect(within(tabla).getByText('1.560,90 €')).toBeInTheDocument()
    expect(screen.queryByText('Estado')).toBeNull()
    expect(screen.queryByText(/Cobrada|Pendiente|Vencida/)).toBeNull()
  })

  it('marca borradores, anuladas y rectificadas junto al número', async () => {
    conSesion(crearSesion())
    conListado([
      fila({ id: 'b1', tipo_documento: 'borrador', num_serie: null, estado: 'borrador' }),
      fila({ id: 'f2', num_serie: 'FAC-2026-0004', estado: 'anulada' }),
      fila({ id: 'f3', num_serie: 'FAC-2026-0003', estado: 'rectificada' }),
      fila({ id: 'f4', num_serie: 'FAC-2026-0002', cliente_nombre: null }),
    ])
    renderApp('/facturas')

    const tabla = await screen.findByRole('table', { name: 'Listado de facturas' })
    const filas = await within(tabla).findAllByRole('row')
    expect(within(filas[1] as HTMLElement).getByText('Borrador')).toBeInTheDocument()
    expect(within(filas[2] as HTMLElement).getByText('Anulada')).toBeInTheDocument()
    expect(within(filas[3] as HTMLElement).getByText('Rectificada')).toBeInTheDocument()
    expect(within(filas[4] as HTMLElement).getByText('Sin cliente')).toBeInTheDocument()
  })

  it('cada borrador tiene su acción «Abrir borrador de…» (FR-049)', async () => {
    conSesion(crearSesion())
    conListado([
      fila({ id: 'b1', tipo_documento: 'borrador', num_serie: null, estado: 'borrador' }),
      fila({
        id: 'b2',
        tipo_documento: 'borrador',
        num_serie: null,
        estado: 'borrador',
        cliente_nombre: null,
      }),
    ])
    renderApp('/facturas')

    const tabla = await screen.findByRole('table', { name: 'Listado de facturas' })
    const abrir = await within(tabla).findAllByRole('link', { name: /^Abrir borrador de / })
    expect(abrir.map((a) => a.getAttribute('aria-label'))).toEqual([
      'Abrir borrador de María López García',
      'Abrir borrador de sin cliente',
    ])
    expect(abrir[0]?.getAttribute('href')).toMatch(/^\/facturas\/borradores\/b1/)
  })

  it('cada factura tiene su acción «Ver factura…» que conserva los filtros', async () => {
    conSesion(crearSesion())
    const facturas = [
      fila(),
      fila({ id: '0192f0c0-0000-7000-8000-0000000f0002', num_serie: 'FAC-2026-0004' }),
    ]
    conListado(facturas)
    renderApp('/facturas?q=maria')

    const tabla = await screen.findByRole('table', { name: 'Listado de facturas' })
    await within(tabla).findByText('FAC-2026-0004')
    const ver = within(tabla).getAllByRole('link', { name: /^Ver factura / })
    expect(ver.map((v) => v.getAttribute('aria-label'))).toEqual([
      'Ver factura FAC-2026-0005',
      'Ver factura FAC-2026-0004',
    ])
    expect(ver[0]?.getAttribute('href')).toMatch(
      new RegExp(`^/facturas/${facturas[0]?.id ?? ''}\\?.*q=maria`),
    )
  })

  it('la búsqueda y los filtros van a la URL (con espera y sin apilar historial) y a la API', async () => {
    conSesion(crearSesion())
    const recibidas = conListado([fila()])
    const { router } = renderApp('/facturas')
    const user = userEvent.setup()

    await user.type(await screen.findByPlaceholderText('Buscar número, cliente o NIF'), 'maria')
    await waitFor(() => {
      expect(router.state.location.search).toMatchObject({ q: 'maria', pagina: 1 })
    })
    await user.click(screen.getByRole('button', { name: /Mes/ }))
    await user.click(await screen.findByRole('option', { name: 'Marzo' }))
    await waitFor(() => {
      expect(router.state.location.search).toMatchObject({ q: 'maria', mes: 3 })
    })
    await user.click(screen.getByRole('button', { name: /Año/ }))
    await user.click(await screen.findByRole('option', { name: 'Todos los años' }))

    await waitFor(() => {
      expect(
        recibidas.some(
          (p) => p.get('q') === 'maria' && p.get('mes') === '3' && p.get('anio') === 'todos',
        ),
      ).toBe(true)
    })
    // `replace`: la búsqueda no deja una entrada de historial por cada cambio.
    expect(router.history.length).toBe(1)
  })

  it('por defecto pide el año en curso sin ponerlo en la URL', async () => {
    conSesion(crearSesion())
    const recibidas = conListado([fila()])
    renderApp('/facturas')

    const anio = await screen.findByRole('button', { name: /Año/ })
    expect(anio).toHaveTextContent(String(anioEnCurso()))
    await waitFor(() => {
      expect(recibidas[0]?.get('anio')).toBeNull()
      expect(recibidas[0]?.get('orden')).toBe('recientes')
    })
  })

  it('sin facturas en el año ofrece ver todos los años', async () => {
    conSesion(crearSesion())
    conListado([], 0)
    const { router } = renderApp('/facturas')
    const user = userEvent.setup()

    expect(await screen.findByText(`No hay facturas en ${String(anioEnCurso())}`)).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Ver todos los años' }))

    await waitFor(() => {
      expect(router.state.location.search).toMatchObject({ anio: 'todos' })
    })
    expect(await screen.findByText('Todavía no hay facturas')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Nueva factura' }).length).toBeGreaterThan(1)
  })

  it('sin resultados de búsqueda, «Limpiar filtros» vuelve a los valores por defecto', async () => {
    conSesion(crearSesion())
    conListado([], 0)
    const { router } = renderApp('/facturas?q=zafiro&mes=3&anio=2025')
    const user = userEvent.setup()

    expect(await screen.findByText('No hay resultados')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Limpiar filtros' }))

    await waitFor(() => {
      expect(router.state.location.search).toEqual({ orden: 'recientes', pagina: 1 })
    })
  })

  it('en móvil presenta cada factura como tarjeta con su acción', async () => {
    conSesion(crearSesion())
    conListado([fila()])
    renderApp('/facturas')

    const tarjetas = await screen.findByRole('list', { name: 'Listado de facturas' })
    expect(tarjetas.className).toContain('md:hidden')
    expect(await within(tarjetas).findByText('FAC-2026-0005')).toBeInTheDocument()
    expect(within(tarjetas).getByText('29/09/2026 · 1.560,90 €')).toBeInTheDocument()
    expect(
      within(tarjetas).getByRole('link', { name: 'Ver factura FAC-2026-0005' }),
    ).toBeInTheDocument()
  })

  it('ignora parámetros no válidos de la URL', async () => {
    conSesion(crearSesion())
    const recibidas = conListado([fila()])
    const { router } = renderApp('/facturas?anio=1999&mes=13&orden=numero')

    await screen.findByRole('table', { name: 'Listado de facturas' })
    expect(router.state.location.search).toEqual({ orden: 'recientes', pagina: 1 })
    await waitFor(() => {
      expect(recibidas[0]?.get('anio')).toBeNull()
      expect(recibidas[0]?.get('mes')).toBeNull()
    })
  })
})
