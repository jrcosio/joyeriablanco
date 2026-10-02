import { expect, type Page } from '@playwright/test'
import { dni, unico } from './entorno'

export interface FacturaCreada {
  id: string
  num_serie: string
}

/** Emite por la API, con la sesión del navegador, una factura a un cliente nuevo: por defecto,
 * de dos líneas con IVA. */
export async function emitirPorLaApi(
  page: Page,
  lineas: { unidades: string; descripcion: string; precio_unitario: string }[] = [
    { unidades: '1', descripcion: 'Anillo', precio_unitario: '1200.00' },
    { unidades: '2', descripcion: 'Ajuste', precio_unitario: '45.00' },
  ],
): Promise<FacturaCreada & { cliente: string }> {
  const sesion = (await (await page.request.get('/api/v1/sesion')).json()) as {
    csrf_token: string
  }
  // Como el navegador: CSRF y origen de la página (la API rechaza otros orígenes).
  const cabeceras = {
    'X-CSRF-Token': sesion.csrf_token,
    Origin: new URL(page.url()).origin,
  }
  const numero = unico()
  const nombre = `Cliente Corrección ${String(numero)}`
  const cliente = await page.request.post('/api/v1/clientes', {
    headers: cabeceras,
    data: {
      tipo: 'particular',
      nombre,
      identificacion_tipo: 'NIF',
      identificacion_numero: dni(numero),
      direccion: 'Calle Recogidas, 12',
      codigo_postal: '18005',
      localidad: 'Granada',
    },
  })
  expect(cliente.status()).toBe(201)
  const { id } = (await cliente.json()) as { id: string }
  const factura = await page.request.post('/api/v1/facturas', {
    headers: { ...cabeceras, 'Idempotency-Key': crypto.randomUUID() },
    data: {
      fecha_expedicion: new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid' }).format(
        new Date(),
      ),
      cliente_id: id,
      lineas,
    },
  })
  expect(factura.status()).toBe(201)
  return { ...((await factura.json()) as FacturaCreada), cliente: nombre }
}
