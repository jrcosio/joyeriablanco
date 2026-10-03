import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PresupuestoSalida } from '../../api/tipos'
import { conCatalogos, conSesion, crearCliente, crearSesion, renderApp } from '../../test/app'
import { conFacturacion, crearBorradorFactura } from '../../test/facturas'
import { server } from '../../test/msw'
import { conPresupuestos, crearPresupuesto } from '../../test/presupuestos'

const ID = '0192f0c0-0000-7000-8000-0000000e0003'
const ORIGEN = { id: ID, num_serie: 'PRE-2026-0003', fecha: '2026-09-29' }
const BORRADOR = crearBorradorFactura({ presupuesto_origen: ORIGEN })

/** La consulta (`antes` y, tras pedir la conversión, `despues`) y la conversión con su respuesta. */
function conConversion(
  antes: PresupuestoSalida,
  conversion: () => Response = () => HttpResponse.json(BORRADOR, { status: 201 }),
  despues: PresupuestoSalida = antes,
) {
  const conversiones: string[] = []
  let lecturasDespues = 0
  server.use(
    http.get(`*/api/v1/presupuestos/${ID}`, () => {
      if (conversiones.length === 0) return HttpResponse.json(antes)
      lecturasDespues += 1
      return HttpResponse.json(despues)
    }),
    http.post(`*/api/v1/presupuestos/${ID}/conversion`, ({ request }) => {
      conversiones.push(request.headers.get('Idempotency-Key') ?? 'sin clave')
      return conversion()
    }),
    http.get(`*/api/v1/borradores-factura/${BORRADOR.id}`, () => HttpResponse.json(BORRADOR)),
    http.get('*/api/v1/clientes', () =>
      HttpResponse.json({ elementos: [crearCliente()], total: 1, pagina: 1, tamano: 25 }),
    ),
    http.get('*/api/v1/clientes/:id', () => HttpResponse.json(crearCliente())),
  )
  return { conversiones, recargas: () => lecturasDespues }
}

async function abrirConfirmacion() {
  const app = renderApp(`/presupuestos/${ID}`)
  const modal = await screen.findByRole('dialog', { name: 'Presupuesto PRE-2026-0003' })
  const user = userEvent.setup()
  await user.click(within(modal).getByRole('button', { name: 'Convertir en factura' }))
  const confirmacion = await screen.findByRole('alertdialog', { name: '¿Convertir en factura?' })
  return { ...app, user, modal, confirmacion }
}

describe('Convertir un presupuesto en factura (005, US3)', () => {
  beforeEach(() => {
    conSesion(crearSesion())
    conCatalogos()
    conPresupuestos()
    conFacturacion()
  })

  it('pide confirmación, sin clave de operación y sin aviso si está vigente', async () => {
    const { conversiones } = conConversion(crearPresupuesto())
    const { confirmacion } = await abrirConfirmacion()

    expect(
      within(confirmacion).getByText(
        'Se creará un borrador de factura con los datos de PRE-2026-0003. Podrás revisarlo antes de emitirlo.',
      ),
    ).toBeInTheDocument()
    expect(within(confirmacion).queryByText(/venció/)).toBeNull()
    expect(conversiones).toEqual([])
  })

  it('un caducado se convierte con el aviso de la validez vencida', async () => {
    conConversion(crearPresupuesto({ estado: 'caducado', valido_hasta: '2026-08-31' }))
    const { confirmacion } = await abrirConfirmacion()

    expect(
      within(confirmacion).getByText('La validez de este presupuesto venció el 31/08/2026.'),
    ).toBeInTheDocument()
  })

  it('al confirmar crea el borrador, avisa, invalida y abre el borrador de factura', async () => {
    const { conversiones } = conConversion(crearPresupuesto())
    const { user, confirmacion, router, queryClient } = await abrirConfirmacion()
    const invalidar = vi.spyOn(queryClient, 'invalidateQueries')

    await user.click(within(confirmacion).getByRole('button', { name: 'Convertir en factura' }))

    expect(
      await screen.findByText('Borrador de factura creado a partir de PRE-2026-0003'),
    ).toBeInTheDocument()
    await waitFor(() => {
      expect(router.state.location.pathname).toBe(`/facturas/borradores/${BORRADOR.id}`)
    })
    const borrador = await screen.findByRole('dialog', { name: 'Borrador' })
    expect(within(borrador).getByText(/Procede del presupuesto/)).toBeInTheDocument()
    expect(within(borrador).getByRole('link', { name: 'PRE-2026-0003' })).toHaveAttribute(
      'href',
      `/presupuestos/${ID}`,
    )
    expect(conversiones).toEqual(['sin clave'])
    const claves = invalidar.mock.calls.map(([filtro]) => filtro?.queryKey)
    expect(claves).toEqual(expect.arrayContaining([['presupuestos'], ['facturas'], ['clientes']]))
  })

  it('una respuesta 200 con el borrador que ya existía también lo abre', async () => {
    conConversion(crearPresupuesto(), () => HttpResponse.json(BORRADOR))
    const { user, confirmacion, router } = await abrirConfirmacion()

    await user.click(within(confirmacion).getByRole('button', { name: 'Convertir en factura' }))

    await waitFor(() => {
      expect(router.state.location.pathname).toBe(`/facturas/borradores/${BORRADOR.id}`)
    })
  })

  it('un 409 presupuesto-no-modificable lo explica, ofrece el borrador y recarga', async () => {
    const enFacturacion = crearPresupuesto({
      estado: 'en_facturacion',
      borrador_factura: { id: BORRADOR.id },
    })
    const { recargas } = conConversion(
      crearPresupuesto(),
      () =>
        HttpResponse.json(
          {
            type: '/problemas/presupuesto-no-modificable',
            title: 'El presupuesto no se puede cambiar',
            status: 409,
            detail:
              'El presupuesto está en facturación: emite o elimina antes su borrador de factura.',
            estado: 'en_facturacion',
            borrador_factura_id: BORRADOR.id,
          },
          { status: 409, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      enFacturacion,
    )
    const { user, confirmacion, modal } = await abrirConfirmacion()

    await user.click(within(confirmacion).getByRole('button', { name: 'Convertir en factura' }))

    expect(await within(modal).findByRole('alert')).toHaveTextContent(
      'El presupuesto está en facturación: emite o elimina antes su borrador de factura. Se muestran sus datos actuales.',
    )
    await waitFor(() => {
      expect(recargas()).toBeGreaterThanOrEqual(1)
    })
    expect(
      await within(modal).findByText('Este presupuesto tiene un borrador de factura en curso.'),
    ).toBeInTheDocument()
    for (const enlace of within(modal).getAllByRole('link', {
      name: 'Abrir borrador de factura',
    })) {
      expect(enlace).toHaveAttribute('href', `/facturas/borradores/${BORRADOR.id}`)
    }
    expect(within(modal).queryByRole('button', { name: 'Convertir en factura' })).toBeNull()
  })
})
