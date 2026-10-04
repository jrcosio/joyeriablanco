import { screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import type { Alarma } from '../../api/tipos'
import { conSesion, crearSesion, renderApp } from '../../test/app'
import { server } from '../../test/msw'

const INTEGRIDAD: Alarma = {
  tipo: 'integridad',
  mensaje:
    'Alarma de integridad: se ha detectado una anomalía en los registros el 03/10/2026 10:15',
  desde: '2026-10-03T08:15:00Z',
  secuencia_afectada: 4,
}
const CERTIFICADO: Alarma = {
  tipo: 'certificado',
  mensaje:
    'No se puede facturar: el certificado de firma no es utilizable (el certificado ha caducado)',
  desde: '2026-10-01T00:00:00Z',
  secuencia_afectada: null,
}

function conAlarmas(alarmas: Alarma[]) {
  server.use(http.get('*/api/v1/alarmas', () => HttpResponse.json({ alarmas })))
}

describe('Banda de alarma (004, FR-019)', () => {
  it('sin alarmas no hay banda', async () => {
    conSesion(crearSesion())
    renderApp('/cuenta')

    await screen.findByRole('heading', { name: 'Mi cuenta' })
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('un empleado ve las dos apiladas, la de integridad primero, sin enlace ni botón de cerrar', async () => {
    conSesion(crearSesion({ rol: 'empleado' }))
    conAlarmas([CERTIFICADO, INTEGRIDAD])
    renderApp('/cuenta')

    const alarmas = await screen.findAllByRole('alert')
    expect(alarmas.map((a) => a.textContent)).toEqual([
      `${INTEGRIDAD.mensaje}.`,
      `${CERTIFICADO.mensaje}.`,
    ])
    for (const alarma of alarmas) {
      expect(within(alarma).queryByRole('link')).toBeNull()
      expect(within(alarma).queryByRole('button')).toBeNull()
    }
  })

  it('un administrador tiene «Ver detalle» en cada una', async () => {
    conSesion(crearSesion({ rol: 'administrador' }))
    conAlarmas([INTEGRIDAD, CERTIFICADO])
    renderApp('/cuenta')

    const [integridad, certificado] = await screen.findAllByRole('alert')
    if (!integridad || !certificado) throw new Error('Faltan alarmas')
    expect(within(integridad).getByRole('link', { name: 'Ver detalle' })).toHaveAttribute(
      'href',
      expect.stringMatching(/^\/registro-fiscal/),
    )
    expect(within(certificado).getByRole('link', { name: 'Ver detalle' })).toHaveAttribute(
      'href',
      '/configuracion/facturacion',
    )
  })
})
