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

  it('el pie ofrece «Imprimir» para cualquier sesión (US2)', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    conPresupuesto(crearPresupuesto())
    renderApp(`/presupuestos/${ID}`)

    const modal = await screen.findByRole('dialog', { name: 'Presupuesto PRE-2026-0003' })
    expect(
      within(modal).getByRole('link', { name: 'Imprimir presupuesto PRE-2026-0003' }),
    ).toHaveAttribute('href', `/api/v1/presupuestos/${ID}/pdf`)
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

  it('un pendiente ofrece «Convertir en factura» a cualquier sesión (US3)', async () => {
    conSesion(crearSesion({ rol: 'empleado' }))
    conPresupuestos()
    conPresupuesto(crearPresupuesto())
    renderApp(`/presupuestos/${ID}`)

    const modal = await screen.findByRole('dialog', { name: 'Presupuesto PRE-2026-0003' })
    expect(within(modal).getByRole('button', { name: 'Convertir en factura' })).toBeInTheDocument()
  })

  it('en facturación avisa y abre su borrador, sin convertir, modificar ni anular (US3)', async () => {
    conSesion(crearSesion({ rol: 'administrador' }))
    conPresupuestos()
    conPresupuesto(crearPresupuesto({ estado: 'en_facturacion', borrador_factura: { id: 'b1' } }))
    renderApp(`/presupuestos/${ID}`)

    const modal = await screen.findByRole('dialog', { name: 'Presupuesto PRE-2026-0003' })
    expect(within(modal).getByText('En facturación')).toBeInTheDocument()
    expect(
      within(modal).getByText('Este presupuesto tiene un borrador de factura en curso.'),
    ).toBeInTheDocument()
    expect(within(modal).getByRole('link', { name: 'Abrir borrador de factura' })).toHaveAttribute(
      'href',
      '/facturas/borradores/b1',
    )
    for (const accion of ['Convertir en factura', 'Modificar', 'Anular']) {
      expect(within(modal).queryByRole('button', { name: accion })).toBeNull()
      expect(within(modal).queryByRole('link', { name: accion })).toBeNull()
    }
  })

  it('un convertido enlaza con su factura y con la vigente si se corrigió (US3, FR-022)', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    conPresupuesto(
      crearPresupuesto({
        estado: 'convertido',
        cierre: {
          tipo: 'conversion',
          motivo_texto: null,
          creado_en: '2026-09-30T10:00:00Z',
          creado_por: { id: 'u1', nombre: 'Ana García', eliminado: false },
          presupuesto_nuevo: null,
          factura: { id: 'f1', num_serie: 'FAC-2026-0012' },
          factura_vigente: { id: 'f2', num_serie: 'FAC-2026-0013' },
        },
      }),
    )
    renderApp(`/presupuestos/${ID}`)

    const modal = await screen.findByRole('dialog', { name: 'Presupuesto PRE-2026-0003' })
    expect(within(modal).getByText('Convertido en factura')).toBeInTheDocument()
    expect(within(modal).getByRole('link', { name: 'FAC-2026-0012' })).toHaveAttribute(
      'href',
      '/facturas/f1',
    )
    expect(within(modal).getByRole('link', { name: 'FAC-2026-0013' })).toHaveAttribute(
      'href',
      '/facturas/f2',
    )
    expect(within(modal).queryByRole('button', { name: 'Convertir en factura' })).toBeNull()
  })
})
