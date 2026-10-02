import { screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import type { PresupuestoSalida } from '../../api/tipos'
import { conSesion, crearSesion, renderApp } from '../../test/app'
import { server } from '../../test/msw'
import { conPresupuestos, crearPresupuesto } from '../../test/presupuestos'

function conPresupuesto(presupuesto: PresupuestoSalida) {
  server.use(
    http.get(`*/api/v1/presupuestos/${presupuesto.id}`, () => HttpResponse.json(presupuesto)),
  )
}

const ID = '0192f0c0-0000-7000-8000-0000000e0003'

describe('Consulta de un presupuesto emitido (005, US1)', () => {
  it('muestra sus datos, la validez, las líneas y los totales, sin campos editables', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    conPresupuesto(crearPresupuesto())
    renderApp(`/presupuestos/${ID}`)

    const modal = await screen.findByRole('dialog', { name: 'Presupuesto PRE-2026-0003' })
    expect(within(modal).getByText('29/10/2026')).toBeInTheDocument()
    expect(
      within(modal).getByRole('table', { name: 'Líneas del presupuesto PRE-2026-0003' }),
    ).toBeInTheDocument()
    expect(within(modal).getByText('Total presupuesto')).toBeInTheDocument()
    expect(within(modal).getByText('1.560,90 €')).toBeInTheDocument()
    expect(within(modal).queryByRole('textbox')).toBeNull()
  })

  it('un sustituido lleva su marca y enlaza con el que lo sustituye (FR-017)', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    conPresupuesto(
      crearPresupuesto({
        estado: 'sustituido',
        vigente_actual: { id: 'n1', num_serie: 'PRE-2026-0009', fecha: '2026-09-30' },
        cierre: {
          tipo: 'sustitucion',
          motivo_texto: 'Otro precio',
          creado_en: '2026-09-30T10:00:00Z',
          creado_por: { id: 'u1', nombre: 'Ana García', eliminado: false },
          presupuesto_nuevo: { id: 'n1', num_serie: 'PRE-2026-0009', fecha: '2026-09-30' },
          factura: null,
          factura_vigente: null,
        },
      }),
    )
    renderApp(`/presupuestos/${ID}`)

    const modal = await screen.findByRole('dialog', { name: 'Presupuesto PRE-2026-0003' })
    expect(within(modal).getAllByText('Sustituido')).toHaveLength(2) // marca e historial
    expect(within(modal).getAllByRole('link', { name: 'PRE-2026-0009' })).toHaveLength(2)
    expect(within(modal).getByText('Otro precio')).toBeInTheDocument()
  })
})
