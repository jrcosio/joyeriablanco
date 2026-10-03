import { expect, type Page } from '@playwright/test'
import { dni, unico } from './entorno'

export interface PresupuestoCreado {
  id: string
  num_serie: string
}

const hoyMadrid = () =>
  new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid' }).format(new Date())

/** Fecha de negocio AAAA-MM-DD más `dias` días. */
export function sumarDias(fecha: string, dias: number): string {
  const [anio = 0, mes = 1, dia = 1] = fecha.split('-').map(Number)
  return new Date(Date.UTC(anio, mes - 1, dia + dias)).toISOString().slice(0, 10)
}

/**
 * Emite por la API, con la sesión del navegador, un presupuesto a un cliente nuevo (005). Como
 * `emitirPorLaApi` de facturas: CSRF, origen de la página e Idempotency-Key.
 */
export async function emitirPresupuestoPorLaApi(
  page: Page,
  lineas: { unidades: string; descripcion: string; precio_unitario: string }[] = [
    { unidades: '1', descripcion: 'Anillo de encargo', precio_unitario: '500.00' },
  ],
): Promise<PresupuestoCreado & { cliente: string }> {
  const sesion = (await (await page.request.get('/api/v1/sesion')).json()) as {
    csrf_token: string
  }
  const cabeceras = {
    'X-CSRF-Token': sesion.csrf_token,
    Origin: new URL(page.url()).origin,
  }
  const numero = unico()
  const nombre = `Cliente Presupuesto ${String(numero)}`
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
  const hoy = hoyMadrid()
  const presupuesto = await page.request.post('/api/v1/presupuestos', {
    headers: { ...cabeceras, 'Idempotency-Key': crypto.randomUUID() },
    data: { fecha: hoy, valido_hasta: sumarDias(hoy, 30), cliente_id: id, lineas },
  })
  expect(presupuesto.status()).toBe(201)
  return { ...((await presupuesto.json()) as PresupuestoCreado), cliente: nombre }
}
