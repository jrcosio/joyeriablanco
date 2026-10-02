import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import type { BorradorPresupuestoSalida } from '../../api/tipos'
import {
  conCatalogos,
  conSesion,
  crearCliente,
  crearSesion,
  problema,
  renderApp,
} from '../../test/app'
import { server } from '../../test/msw'
import { conPresupuestos, crearPresupuesto } from '../../test/presupuestos'

const maria = crearCliente({ direccion: 'Calle Serrano, 45', localidad: 'Madrid' })
const USUARIO = { id: 'u1', nombre: 'Ana García', eliminado: false }

function borrador(parcial: Partial<BorradorPresupuestoSalida> = {}): BorradorPresupuestoSalida {
  return {
    id: 'b1',
    version: 3,
    fecha: '2026-09-20',
    valido_hasta: '2026-12-31', // elegida a mano: no sigue a la fecha
    cliente: {
      id: maria.id,
      nombre: 'María López García',
      identificacion_pais: 'ES',
      identificacion_tipo: 'NIF',
      identificacion_numero: '12345678Z',
      direccion: 'Calle Serrano, 45',
      codigo_postal: '28001',
      localidad: 'Madrid',
      provincia: 'Madrid',
      pais: 'ES',
      activo: true,
    },
    lineas: [
      {
        orden: 1,
        unidades: '1.00',
        descripcion: 'Anillo',
        precio_unitario: '1200.00',
        importe: '1200.00',
      },
    ],
    oro_inversion: false,
    mencion_exencion: null,
    totales_previstos: {
      desglose: [{ tipo_iva: '21.00', base: '1200.00', cuota: '252.00' }],
      base_total: '1200.00',
      cuota_total: '252.00',
      importe_total: '1452.00',
    },
    tipo_iva_previsto: '21.00',
    creado_en: '2026-09-20T08:00:00Z',
    creado_por: USUARIO,
    actualizado_en: '2026-09-20T08:00:00Z',
    actualizado_por: USUARIO,
    ...parcial,
  }
}

function conBorrador(datos: BorradorPresupuestoSalida = borrador()) {
  const guardados: Record<string, unknown>[] = []
  const emitidos: Record<string, unknown>[] = []
  let eliminado = false
  server.use(
    http.get('*/api/v1/clientes/:id', () => HttpResponse.json(maria)),
    http.get('*/api/v1/borradores-presupuesto/b1', () => HttpResponse.json(datos)),
    http.put('*/api/v1/borradores-presupuesto/b1', async ({ request }) => {
      guardados.push((await request.json()) as Record<string, unknown>)
      return problema(409, 'conflicto-version', 'El borrador ha cambiado desde que lo abriste.')
    }),
    http.post('*/api/v1/borradores-presupuesto/b1/emision', async ({ request }) => {
      emitidos.push((await request.json()) as Record<string, unknown>)
      return HttpResponse.json(crearPresupuesto({ num_serie: 'PRE-2026-0007' }), { status: 201 })
    }),
    http.delete('*/api/v1/borradores-presupuesto/b1', () => {
      eliminado = true
      return new HttpResponse(null, { status: 204 })
    }),
  )
  return { guardados, emitidos, eliminado: () => eliminado }
}

describe('Modal «Borrador de presupuesto» (005, US1)', () => {
  beforeEach(() => {
    conCatalogos()
  })

  it('abre con sus datos, su validez elegida y «Eliminar borrador»', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    conBorrador()
    renderApp('/presupuestos/borradores/b1')

    const modal = await screen.findByRole('dialog', { name: 'Borrador de presupuesto' })
    expect(await within(modal).findByLabelText(/^Fecha/)).toHaveValue('2026-09-20')
    expect(within(modal).getByLabelText(/Válido hasta/)).toHaveValue('2026-12-31')
    expect(within(modal).getByRole('textbox', { name: 'Descripción de la línea 1' })).toHaveValue(
      'Anillo',
    )
    expect(within(modal).getByRole('button', { name: 'Eliminar borrador' })).toBeInTheDocument()
  })

  it('una validez elegida a mano no se recalcula al cambiar la fecha', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    conBorrador()
    renderApp('/presupuestos/borradores/b1')
    const user = userEvent.setup()

    const modal = await screen.findByRole('dialog', { name: 'Borrador de presupuesto' })
    const fecha = await within(modal).findByLabelText(/^Fecha/)
    await user.clear(fecha)
    await user.type(fecha, '2026-09-25')

    expect(within(modal).getByLabelText(/Válido hasta/)).toHaveValue('2026-12-31')
  })

  it('el conflicto de versión se avisa sin sobrescribir (FR-013)', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    const { guardados } = conBorrador()
    renderApp('/presupuestos/borradores/b1')
    const user = userEvent.setup()

    const modal = await screen.findByRole('dialog', { name: 'Borrador de presupuesto' })
    const descripcion = await within(modal).findByRole('textbox', {
      name: 'Descripción de la línea 1',
    })
    await user.type(descripcion, ' de oro')
    await user.click(within(modal).getByRole('button', { name: 'Guardar borrador' }))

    expect(
      await screen.findByRole('alertdialog', { name: 'El borrador ha cambiado' }),
    ).toBeInTheDocument()
    expect(guardados[0]).toMatchObject({ version: 3 })
  })

  it('emitir el borrador envía su versión y su contenido', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    const { emitidos } = conBorrador()
    renderApp('/presupuestos/borradores/b1')
    const user = userEvent.setup()

    const modal = await screen.findByRole('dialog', { name: 'Borrador de presupuesto' })
    await within(modal).findByLabelText(/^Fecha/)
    await user.click(within(modal).getByRole('button', { name: 'Emitir presupuesto' }))
    const confirmacion = await screen.findByRole('alertdialog', {
      name: '¿Emitir el presupuesto?',
    })
    await user.click(within(confirmacion).getByRole('button', { name: 'Emitir presupuesto' }))

    expect(await screen.findByText('Presupuesto PRE-2026-0007 emitido')).toBeInTheDocument()
    expect(emitidos[0]).toMatchObject({
      version: 3,
      fecha: '2026-09-20',
      valido_hasta: '2026-12-31',
      cliente_id: maria.id,
    })
  })

  it('eliminar el borrador pide confirmación', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    const estado = conBorrador()
    renderApp('/presupuestos/borradores/b1')
    const user = userEvent.setup()

    const modal = await screen.findByRole('dialog', { name: 'Borrador de presupuesto' })
    await user.click(await within(modal).findByRole('button', { name: 'Eliminar borrador' }))
    const confirmacion = await screen.findByRole('alertdialog', { name: '¿Eliminar el borrador?' })
    await user.click(within(confirmacion).getByRole('button', { name: 'Eliminar borrador' }))

    expect(await screen.findByText('Borrador eliminado')).toBeInTheDocument()
    expect(estado.eliminado()).toBe(true)
  })
})
