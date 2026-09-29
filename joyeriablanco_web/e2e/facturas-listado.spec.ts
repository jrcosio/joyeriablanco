import { expect, test, type Locator, type Page } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'

/**
 * Listado de facturas con los datos de ejemplo (US3, SC-010): unas 50 facturas de los últimos seis
 * meses (R-16). A 1440 px se ven todas las columnas (R-12).
 */

const COLUMNA = { numero: 1, fecha: 2, cliente: 3, nif: 4, total: 7 } as const

function tabla(page: Page): Locator {
  return page.getByRole('table', { name: 'Listado de facturas' })
}

/** Celdas de la primera fila que es una factura emitida (los borradores de hoy van arriba). */
async function primeraFactura(page: Page) {
  const numeros = await columna(page, COLUMNA.numero)
  const indice = numeros.findIndex((n) => n.startsWith('FAC-'))
  expect(indice).toBeGreaterThanOrEqual(0)
  const celda = async (n: number) => (await columna(page, n))[indice] ?? ''
  return {
    numero: numeros[indice] ?? '',
    cliente: await celda(COLUMNA.cliente),
    nif: await celda(COLUMNA.nif),
  }
}

/** Destinos de las acciones de la página: identifican cada fila, sea borrador o factura. */
async function destinos(page: Page): Promise<string[]> {
  const enlaces = tabla(page).getByRole('link', { name: /^(Ver factura|Abrir borrador de) / })
  await expect(enlaces.first()).toBeVisible()
  return Promise.all((await enlaces.all()).map(async (e) => (await e.getAttribute('href')) ?? ''))
}

async function columna(page: Page, n: number): Promise<string[]> {
  const celdas = tabla(page).locator(`tbody tr td:nth-child(${String(n)})`)
  await expect(celdas.first()).toBeVisible()
  return (await celdas.allTextContents()).map((t) => t.trim())
}

/** «1.560,90 €» → 156090 céntimos. */
function centimos(texto: string): number {
  return Number(texto.replace(/[^\d,]/g, '').replace(',', ''))
}

function sinTildes(texto: string): string {
  return texto.normalize('NFD').replace(/\p{Diacritic}/gu, '')
}

async function buscar(page: Page, texto: string) {
  const respuesta = page.waitForResponse(
    (r) => r.url().includes('/api/v1/facturas?') && r.url().includes('q='),
  )
  await page.getByPlaceholder('Buscar número, cliente o NIF').fill(texto)
  await respuesta
}

async function elegir(page: Page, filtro: RegExp, opcion: string) {
  await page.getByRole('button', { name: filtro }).click()
  await page.getByRole('option', { name: opcion, exact: true }).click()
}

test.describe('Listado de facturas (US3)', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await iniciarSesion(page, 'empleado.demo')
    await page.getByRole('link', { name: 'Facturas' }).click()
    await expect(tabla(page).locator('tbody tr').first()).toBeVisible()
  })

  test('búsqueda por número, por cliente sin tildes ni mayúsculas y por NIF con separadores', async ({
    page,
  }) => {
    const { numero, cliente, nif } = await primeraFactura(page)

    // Parte del número, sin la serie.
    const parte = numero.replace(/^FAC-/, '')
    await buscar(page, parte)
    await expect(page).toHaveURL(new RegExp(`q=${parte}`))
    expect((await columna(page, COLUMNA.numero)).filter((n) => n.startsWith('FAC-'))).toEqual([
      numero,
    ])

    // Cliente en minúsculas y sin tildes.
    await buscar(page, sinTildes(cliente).toLowerCase())
    const clientes = await columna(page, COLUMNA.cliente)
    expect(clientes.length).toBeGreaterThan(0)
    expect(clientes.every((c) => c === cliente)).toBe(true)

    // NIF con puntos y guion.
    const conSeparadores = nif.replace(/^(\d{2})(\d{3})(\d{3})(.)$/, '$1.$2.$3-$4')
    await buscar(page, conSeparadores)
    const nifs = await columna(page, COLUMNA.nif)
    expect(nifs.length).toBeGreaterThan(0)
    expect(nifs.every((n) => n === nif)).toBe(true)
  })

  test('filtros de año y mes, con «Ver todos los años»', async ({ page }) => {
    const anio = new Date().getFullYear()

    await elegir(page, /Año/, String(anio - 1))
    await expect(page).toHaveURL(new RegExp(`anio=${String(anio - 1)}`))
    await expect(page.getByText(`No hay facturas en ${String(anio - 1)}`)).toBeVisible()
    await page.getByRole('button', { name: 'Ver todos los años' }).click()
    await expect(page).toHaveURL(/anio=todos/)
    await expect(tabla(page).locator('tbody tr').first()).toBeVisible()

    // Mes: el de la primera factura (la más reciente); todas las filas son de ese mes.
    const [fecha = ''] = await columna(page, COLUMNA.fecha)
    const mes = Number(fecha.split('/')[1])
    const nombreMes = new Intl.DateTimeFormat('es-ES', { month: 'long' }).format(
      new Date(anio, mes - 1, 1),
    )
    await elegir(page, /Mes/, nombreMes.charAt(0).toUpperCase() + nombreMes.slice(1))
    await expect(page).toHaveURL(new RegExp(`mes=${String(mes)}`))
    const fechas = await columna(page, COLUMNA.fecha)
    expect(fechas.every((f) => Number(f.split('/')[1]) === mes)).toBe(true)
  })

  test('orden por total y paginación, con el estado en la URL al recargar', async ({ page }) => {
    await elegir(page, /Año/, 'Todos los años')
    await elegir(page, /Ordenar/, 'Total mayor')
    await expect(page).toHaveURL(/orden=total_desc/)
    await expect
      .poll(async () => {
        const totales = (await columna(page, COLUMNA.total)).map(centimos)
        return totales.every((t, i) => i === 0 || t <= (totales[i - 1] ?? t))
      })
      .toBe(true)
    const primeraPagina = await destinos(page)
    expect(primeraPagina).toHaveLength(25)

    await page.getByRole('button', { name: 'Página siguiente' }).click()
    await expect(page).toHaveURL(/pagina=2/)
    await expect.poll(async () => (await destinos(page))[0]).not.toBe(primeraPagina[0])
    const segundaPagina = await destinos(page)
    expect(segundaPagina.some((d) => primeraPagina.includes(d))).toBe(false)
    const [primerTotal = ''] = await columna(page, COLUMNA.total)

    await page.reload()
    await expect(page.getByRole('button', { name: /Ordenar/ })).toContainText('Total mayor')
    await expect(page.getByRole('button', { name: /Año/ })).toContainText('Todos los años')
    expect(await destinos(page)).toEqual(segundaPagina)
    expect((await columna(page, COLUMNA.total))[0]).toBe(primerTotal)
  })
})
