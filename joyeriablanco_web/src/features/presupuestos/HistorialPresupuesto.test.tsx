import { screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import type { CierrePresupuestoSalida, PresupuestoSalida } from '../../api/tipos'
import { conSesion, crearSesion, renderApp } from '../../test/app'
import { server } from '../../test/msw'
import { conPresupuestos, crearPresupuesto } from '../../test/presupuestos'

const ID = '0192f0c0-0000-7000-8000-0000000e0003'
const AUTOR = { id: 'u2', nombre: 'Luis Martín', eliminado: false }

function cierre(parcial: Partial<CierrePresupuestoSalida>): CierrePresupuestoSalida {
  return {
    tipo: 'anulacion',
    motivo_texto: null,
    creado_en: '2026-09-30T10:00:00Z',
    creado_por: AUTOR,
    presupuesto_nuevo: null,
    factura: null,
    factura_vigente: null,
    ...parcial,
  }
}

async function historial(presupuesto: PresupuestoSalida) {
  server.use(http.get(`*/api/v1/presupuestos/${ID}`, () => HttpResponse.json(presupuesto)))
  renderApp(`/presupuestos/${ID}`)
  const modal = await screen.findByRole('dialog', { name: 'Presupuesto PRE-2026-0003' })
  return { modal, seccion: within(modal).queryByRole('heading', { name: 'Historial' }) }
}

describe('Historial de un presupuesto (005, FR-017)', () => {
  beforeEach(() => {
    conSesion(crearSesion())
    conPresupuestos()
  })

  it('un pendiente no tiene historial', async () => {
    const { seccion } = await historial(crearPresupuesto())

    expect(seccion).toBeNull()
  })

  it('una anulación, con su fecha, su autor y su motivo', async () => {
    const { modal } = await historial(
      crearPresupuesto({
        estado: 'anulado',
        cierre: cierre({ tipo: 'anulacion', motivo_texto: 'Rechazado por el cliente' }),
      }),
    )

    expect(within(modal).getAllByText('Anulado')).toHaveLength(2)
    expect(within(modal).getByText('Luis Martín')).toBeInTheDocument()
    expect(within(modal).getByText('Rechazado por el cliente')).toBeInTheDocument()
  })

  it('una sustitución enlaza con el presupuesto nuevo', async () => {
    const nuevo = { id: 'n1', num_serie: 'PRE-2026-0009', fecha: '2026-09-30' }
    const { modal } = await historial(
      crearPresupuesto({
        estado: 'sustituido',
        vigente_actual: nuevo,
        cierre: cierre({
          tipo: 'sustitucion',
          motivo_texto: 'Otro precio',
          presupuesto_nuevo: nuevo,
        }),
      }),
    )

    expect(within(modal).getByText('Presupuesto nuevo')).toBeInTheDocument()
    for (const enlace of within(modal).getAllByRole('link', { name: 'PRE-2026-0009' })) {
      expect(enlace).toHaveAttribute('href', expect.stringMatching(/^\/presupuestos\/n1(\?|$)/))
    }
  })

  it('una conversión enlaza con la factura', async () => {
    const { modal } = await historial(
      crearPresupuesto({
        estado: 'convertido',
        cierre: cierre({ tipo: 'conversion', factura: { id: 'f1', num_serie: 'FAC-2026-0012' } }),
      }),
    )

    expect(within(modal).getByText('Convertido en factura')).toBeInTheDocument()
    expect(within(modal).getByRole('link', { name: 'FAC-2026-0012' })).toHaveAttribute(
      'href',
      '/facturas/f1',
    )
  })

  it('el que sustituye a otro lo dice y lo enlaza', async () => {
    const { modal, seccion } = await historial(
      crearPresupuesto({
        sustituye_a: { id: 'o1', num_serie: 'PRE-2026-0001', fecha: '2026-09-01' },
      }),
    )

    expect(within(modal).getByText(/Sustituye a/)).toBeInTheDocument()
    expect(within(modal).getByRole('link', { name: 'PRE-2026-0001' })).toHaveAttribute(
      'href',
      expect.stringMatching(/^\/presupuestos\/o1(\?|$)/),
    )
    expect(seccion).toBeNull()
  })
})
