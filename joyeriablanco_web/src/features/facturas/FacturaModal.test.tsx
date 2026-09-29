import { screen, waitFor, within } from '@testing-library/react'
import userEvent, { type UserEvent } from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import type { ParametrosFacturacionSalida } from '../../api/tipos'
import {
  conCatalogos,
  conSesion,
  crearCliente,
  crearSesion,
  problema,
  renderApp,
} from '../../test/app'
import { conFacturacion, crearFactura, PARAMETROS } from '../../test/facturas'
import { server } from '../../test/msw'

const maria = crearCliente({ direccion: 'Calle Serrano, 45', localidad: 'Madrid' })

interface Emision {
  cuerpo: unknown
  clave: string | null
}

function conEmision(respuestas: (() => Response)[] = []) {
  const emisiones: Emision[] = []
  server.use(
    http.get('*/api/v1/clientes', () =>
      HttpResponse.json({ elementos: [maria], total: 1, pagina: 1, tamano: 25 }),
    ),
    http.get('*/api/v1/clientes/:id', () => HttpResponse.json(maria)),
    http.post('*/api/v1/facturas', async ({ request }) => {
      emisiones.push({
        cuerpo: await request.json(),
        clave: request.headers.get('Idempotency-Key'),
      })
      const respuesta = respuestas[emisiones.length - 1]
      return respuesta
        ? respuesta()
        : HttpResponse.json(crearFactura({ num_serie: 'FAC-2026-0006' }), { status: 201 })
    }),
  )
  return emisiones
}

/** Espera a que el modal tenga los parámetros de facturación (antes solo muestra la carga). */
async function modalListo() {
  await screen.findByText('Se asigna al emitir')
  return screen.getByRole('dialog', { name: 'Nueva factura' })
}

async function elegirCliente(user: UserEvent) {
  await modalListo()
  await user.type(screen.getByRole('combobox', { name: /Cliente/ }), 'maria')
  await user.click(await screen.findByRole('option', { name: /María López García/ }))
}

async function escribirLineas(user: UserEvent) {
  await user.type(screen.getByRole('textbox', { name: 'Descripción de la línea 1' }), 'Anillo')
  await user.type(
    screen.getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' }),
    '1.200',
  )
  await user.click(screen.getByRole('button', { name: 'Añadir línea' }))
  const unidades = screen.getByRole('textbox', { name: 'Unidades de la línea 2' })
  await user.clear(unidades)
  await user.type(unidades, '2')
  await user.type(screen.getByRole('textbox', { name: 'Descripción de la línea 2' }), 'Ajuste')
  await user.type(
    screen.getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 2' }),
    '45',
  )
}

async function emitir(user: UserEvent) {
  await user.click(screen.getByRole('button', { name: 'Emitir factura' }))
  const confirmacion = await screen.findByRole('alertdialog', { name: '¿Emitir la factura?' })
  await user.click(within(confirmacion).getByRole('button', { name: 'Emitir factura' }))
}

describe('Modal «Nueva factura» (US2)', () => {
  beforeEach(() => {
    conCatalogos()
  })

  it('tiene las tres secciones y el número se asigna al emitir', async () => {
    conSesion(crearSesion())
    conFacturacion()
    renderApp('/facturas/nueva')

    const modal = await modalListo()
    expect(within(modal).getByRole('heading', { name: 'Datos de emisión' })).toBeInTheDocument()
    expect(
      within(modal).getByRole('heading', { name: 'Detalle de la factura' }),
    ).toBeInTheDocument()
    expect(within(modal).getByText('FAC-2026-0006')).toBeInTheDocument()
    expect(within(modal).getByLabelText(/Fecha/)).toHaveValue(PARAMETROS.hoy)
  })

  it('muestra el cliente elegido y previsualiza los importes de la captura', async () => {
    conSesion(crearSesion())
    conFacturacion()
    conEmision()
    renderApp('/facturas/nueva')
    const user = userEvent.setup()

    await elegirCliente(user)
    expect(await screen.findByText('Calle Serrano, 45')).toBeInTheDocument()
    await escribirLineas(user)

    const totales = screen.getByText('Total factura').closest('dl')
    expect(totales).not.toBeNull()
    expect(within(totales as HTMLElement).getByText('1.290,00 €')).toBeInTheDocument()
    expect(within(totales as HTMLElement).getByText('IVA (21 %)')).toBeInTheDocument()
    expect(within(totales as HTMLElement).getByText('270,90 €')).toBeInTheDocument()
    expect(within(totales as HTMLElement).getByText('1.560,90 €')).toBeInTheDocument()
  })

  it('emite tras confirmar, sin enviar importes calculados y con clave de operación', async () => {
    conSesion(crearSesion())
    conFacturacion()
    const emisiones = conEmision()
    const { router } = renderApp('/facturas/nueva')
    const user = userEvent.setup()

    await elegirCliente(user)
    await escribirLineas(user)
    await emitir(user)

    expect(await screen.findByText('Factura FAC-2026-0006 emitida')).toBeInTheDocument()
    expect(emisiones).toHaveLength(1)
    expect(emisiones[0]?.cuerpo).toEqual({
      fecha_expedicion: PARAMETROS.hoy,
      cliente_id: maria.id,
      lineas: [
        { unidades: '1.00', descripcion: 'Anillo', precio_unitario: '1200.00' },
        { unidades: '2.00', descripcion: 'Ajuste', precio_unitario: '45.00' },
      ],
    })
    expect(emisiones[0]?.clave).toMatch(/^[0-9a-f-]{36}$/)
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/facturas')
    })
  })

  it('reintenta con la MISMA clave tras un fallo de red (no duplica la factura)', async () => {
    conSesion(crearSesion())
    conFacturacion()
    const emisiones = conEmision([
      () => HttpResponse.error(),
      // La primera llegó a emitirse: la repetición con la misma clave devuelve esa factura.
      () => HttpResponse.json(crearFactura({ num_serie: 'FAC-2026-0007' }), { status: 200 }),
    ])
    renderApp('/facturas/nueva')
    const user = userEvent.setup()

    await elegirCliente(user)
    await escribirLineas(user)
    await emitir(user)
    expect(await screen.findByText(/Tus datos siguen aquí/)).toBeInTheDocument()
    await emitir(user)

    expect(await screen.findByText('Factura FAC-2026-0007 emitida')).toBeInTheDocument()
    expect(emisiones.map((e) => e.clave)).toEqual([emisiones[0]?.clave, emisiones[0]?.clave])
  })

  it('con la sesión caducada avisa, vuelve al acceso y no conserva lo tecleado', async () => {
    conSesion(crearSesion())
    conFacturacion()
    conEmision([() => problema(401, 'no-autenticado', 'Sesión no válida')])
    const { router } = renderApp('/facturas/nueva')
    const user = userEvent.setup()

    await elegirCliente(user)
    await escribirLineas(user)
    conSesion(null)
    await emitir(user)

    expect(await screen.findByText(/Tu sesión ha caducado/)).toBeInTheDocument()
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/acceso')
    })
    expect(screen.queryByRole('dialog', { name: 'Nueva factura' })).not.toBeInTheDocument()
  })

  it('pide el cliente antes de confirmar la emisión', async () => {
    conSesion(crearSesion())
    conFacturacion()
    conEmision()
    renderApp('/facturas/nueva')
    const user = userEvent.setup()

    await modalListo()
    await escribirLineas(user)
    await user.click(screen.getByRole('button', { name: 'Emitir factura' }))

    expect(await screen.findByText('Elige el cliente.')).toBeInTheDocument()
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
  })

  it('lleva los errores del servidor a su campo', async () => {
    conSesion(crearSesion())
    conFacturacion()
    conEmision([
      () =>
        HttpResponse.json(
          {
            type: '/problemas/validacion',
            title: 'Datos no válidos',
            status: 422,
            errores: [{ campo: 'lineas.1.precio_unitario', mensaje: 'Precio demasiado alto.' }],
          },
          { status: 422, headers: { 'Content-Type': 'application/problem+json' } },
        ),
    ])
    renderApp('/facturas/nueva')
    const user = userEvent.setup()

    await elegirCliente(user)
    await escribirLineas(user)
    await emitir(user)

    expect(await screen.findByText('Precio demasiado alto.')).toBeInTheDocument()
    expect(
      screen.getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 2' }),
    ).toHaveAttribute('aria-invalid', 'true')
  })

  it('no deja emitir si falta configuración y explica qué falta', async () => {
    const parametros: ParametrosFacturacionSalida = {
      ...PARAMETROS,
      emision_posible: false,
      faltan: ['modalidad'],
    }
    conSesion(crearSesion())
    conFacturacion(parametros)
    renderApp('/facturas/nueva')

    await modalListo()
    expect(screen.getByRole('button', { name: 'Emitir factura' })).toBeDisabled()
    expect(screen.getByText(/falta Modalidad del sistema de facturación/)).toBeInTheDocument()
    expect(screen.getByText(/Un administrador debe completarlo/)).toBeInTheDocument()
  })

  it('pide confirmación antes de descartar lo escrito', async () => {
    conSesion(crearSesion())
    conFacturacion()
    renderApp('/facturas/nueva')
    const user = userEvent.setup()

    await modalListo()
    await user.type(screen.getByRole('textbox', { name: 'Descripción de la línea 1' }), 'Anillo')
    await user.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(
      await screen.findByRole('alertdialog', { name: '¿Descartar los cambios?' }),
    ).toBeInTheDocument()
  })

  it('se pueden quitar todas las líneas y añadir de nuevo', async () => {
    conSesion(crearSesion())
    conFacturacion()
    renderApp('/facturas/nueva')
    const user = userEvent.setup()

    await modalListo()
    await user.click(screen.getByRole('button', { name: 'Quitar la línea 1' }))
    expect(screen.getByText('Añade la primera línea.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Añadir línea' }))

    expect(screen.getByRole('textbox', { name: 'Descripción de la línea 1' })).toBeInTheDocument()
  })
})
