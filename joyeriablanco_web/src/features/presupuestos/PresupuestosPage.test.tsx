import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import type { PresupuestoResumenSalida } from '../../api/tipos'
import { anioEnCurso } from '../../lib/fechas'
import { conSesion, crearSesion, renderApp } from '../../test/app'
import { server } from '../../test/msw'
import { filaPresupuesto } from '../../test/presupuestos'

function conListado(elementos: PresupuestoResumenSalida[], total = elementos.length) {
  const recibidas: URLSearchParams[] = []
  server.use(
    http.get('*/api/v1/presupuestos', ({ request }) => {
      recibidas.push(new URL(request.url).searchParams)
      return HttpResponse.json({ elementos, total, pagina: 1, tamano: 25 })
    }),
  )
  return recibidas
}

describe('Listado de presupuestos (005, US1)', () => {
  it('las columnas del listado de facturas, sin columna de estado (FR-024)', async () => {
    conSesion(crearSesion())
    conListado([filaPresupuesto()])
    renderApp('/presupuestos')

    const tabla = await screen.findByRole('table', { name: 'Listado de presupuestos' })
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
    await within(tabla).findByText('PRE-2026-0003')
    expect(within(tabla).getByText('1.560,90 €')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Nuevo presupuesto' })).toBeInTheDocument()
  })

  it('cada estado lleva su marca con texto, y un pendiente ninguna (FR-024)', async () => {
    conSesion(crearSesion())
    conListado([
      filaPresupuesto({
        id: 'b1',
        tipo_documento: 'borrador',
        num_serie: null,
        estado: 'borrador',
      }),
      filaPresupuesto({ id: 'p1', num_serie: 'PRE-2026-0001', estado: 'pendiente' }),
      filaPresupuesto({ id: 'p2', num_serie: 'PRE-2026-0002', estado: 'caducado' }),
      filaPresupuesto({ id: 'p3', num_serie: 'PRE-2026-0003', estado: 'en_facturacion' }),
      filaPresupuesto({ id: 'p4', num_serie: 'PRE-2026-0004', estado: 'convertido' }),
      filaPresupuesto({ id: 'p5', num_serie: 'PRE-2026-0005', estado: 'sustituido' }),
      filaPresupuesto({ id: 'p6', num_serie: 'PRE-2026-0006', estado: 'anulado' }),
    ])
    renderApp('/presupuestos')

    const tabla = await screen.findByRole('table', { name: 'Listado de presupuestos' })
    for (const marca of [
      'Borrador',
      'Caducado',
      'En facturación',
      'Convertido',
      'Sustituido',
      'Anulado',
    ]) {
      expect(await within(tabla).findByText(marca)).toBeInTheDocument()
    }
    expect(within(tabla).queryByText('Pendiente')).toBeNull()
    expect(
      within(tabla).getByRole('link', { name: 'Abrir borrador de María López García' }),
    ).toBeInTheDocument()
    expect(
      within(tabla).getByRole('link', { name: 'Ver presupuesto PRE-2026-0002' }),
    ).toHaveAttribute('href', expect.stringContaining('/presupuestos/p2'))
  })

  it('los filtros viven en la URL y se envían a la API (FR-025)', async () => {
    conSesion(crearSesion())
    const recibidas = conListado([filaPresupuesto()])
    renderApp('/presupuestos?q=maria&anio=todos&mes=3&orden=total_desc')

    const tabla = await screen.findByRole('table', { name: 'Listado de presupuestos' })
    await within(tabla).findByText('PRE-2026-0003')
    const ultima = recibidas.at(-1)
    expect(ultima?.get('q')).toBe('maria')
    expect(ultima?.get('anio')).toBe('todos')
    expect(ultima?.get('mes')).toBe('3')
    expect(ultima?.get('orden')).toBe('total_desc')
    expect(screen.getByRole('search', { name: 'Filtrar presupuestos' })).toBeInTheDocument()
  })

  it('estados vacíos: todavía ninguno, año sin presupuestos y sin resultados (FR-023)', async () => {
    conSesion(crearSesion())
    conListado([])
    const { unmount } = renderApp('/presupuestos?anio=todos')
    expect(await screen.findByText('Todavía no hay presupuestos')).toBeInTheDocument()
    unmount()

    renderApp('/presupuestos')
    expect(
      await screen.findByText(`No hay presupuestos en ${String(anioEnCurso())}`),
    ).toBeInTheDocument()
    const user = userEvent.setup()
    expect(screen.getByRole('button', { name: 'Ver todos los años' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Ver todos los años' }))
    expect(await screen.findByText('Todavía no hay presupuestos')).toBeInTheDocument()
  })
})
