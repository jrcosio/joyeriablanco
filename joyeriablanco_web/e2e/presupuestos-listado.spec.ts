import { expect, test, type Locator, type Page } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'

/**
 * Listado de presupuestos con los datos de ejemplo (005, US5; FR-036): unos 30 presupuestos de
 * varios meses en todos los estados y tres borradores. A 1440 px se ven todas las columnas.
 */

const COLUMNA = { numero: 1, fecha: 2, cliente: 3, nif: 4, total: 7 } as const

function tabla(page: Page): Locator {
  return page.getByRole('table', { name: 'Listado de presupuestos' })
}

async function columna(page: Page, n: number): Promise<string[]> {
  const celdas = tabla(page).locator(`tbody tr td:nth-child(${String(n)})`)
  await expect(celdas.first()).toBeVisible()
  return (await celdas.allTextContents()).map((t) => t.trim())
}

/** Destinos de las acciones: identifican cada fila, sea borrador o presupuesto. */
async function destinos(page: Page): Promise<string[]> {
  const enlaces = tabla(page).getByRole('link', { name: /^(Ver presupuesto|Abrir borrador de) / })
  await expect(enlaces.first()).toBeVisible()
  return Promise.all((await enlaces.all()).map(async (e) => (await e.getAttribute('href')) ?? ''))
}

/** «1.560,90 €» → 156090 céntimos. */
function centimos(texto: string): number {
  return Number(texto.replace(/[^\d,]/g, '').replace(',', ''))
}

function sinTildes(texto: string): string {
  return texto.normalize('NFD').replace(/\p{Diacritic}/gu, '')
}

async function elegir(page: Page, filtro: RegExp, opcion: string) {
  await page.getByRole('button', { name: filtro }).click()
  await page.getByRole('option', { name: opcion, exact: true }).click()
}

/** Pasa a la página siguiente y espera a que llegue: el listado conserva la anterior mientras. */
async function siguientePagina(page: Page) {
  const respuesta = page.waitForResponse(
    (r) => r.url().includes('/api/v1/presupuestos?') && r.url().includes('pagina=2'),
  )
  await page.getByRole('button', { name: 'Página siguiente' }).click()
  await respuesta
  await expect(page).toHaveURL(/pagina=2/)
}

async function marcas(page: Page): Promise<Set<string>> {
  const textos = await columna(page, COLUMNA.numero)
  return new Set(
    textos.flatMap((t) =>
      ['Borrador', 'En facturación', 'Caducado', 'Convertido', 'Sustituido', 'Anulado'].filter(
        (m) => t.includes(m),
      ),
    ),
  )
}

test.describe('Listado de presupuestos (005, US1 y US5)', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await iniciarSesion(page, 'empleado.demo')
    await page
      .getByRole('navigation', { name: 'Navegación principal' })
      .getByRole('link', { name: 'Presupuestos' })
      .click()
    await expect(page.getByRole('heading', { name: 'Presupuestos' })).toBeVisible()
    // Los más antiguos de ejemplo pueden ser del año anterior: se ven todos.
    await elegir(page, /Año/, 'Todos los años')
    await expect(page).toHaveURL(/anio=todos/)
    await expect(tabla(page).locator('tbody tr').first()).toBeVisible()
  })

  test('los datos de ejemplo traen todos los estados, con sus marcas', async ({ page }) => {
    const vistas = await marcas(page)
    await siguientePagina(page)
    await expect.poll(async () => (await marcas(page)).size).toBeGreaterThan(0)
    for (const marca of await marcas(page)) vistas.add(marca)

    expect([...vistas].sort()).toEqual(
      ['Anulado', 'Borrador', 'Caducado', 'Convertido', 'En facturación', 'Sustituido'].sort(),
    )
  })

  test('búsqueda por número y por cliente sin tildes, y filtro de mes', async ({ page }) => {
    const numeros = await columna(page, COLUMNA.numero)
    const indice = numeros.findIndex((n) => n.startsWith('PRE-'))
    const numero = /PRE-\d{4}-\d{4,}/.exec(numeros[indice] ?? '')?.[0] ?? ''
    const cliente = (await columna(page, COLUMNA.cliente))[indice] ?? ''
    expect(numero).not.toBe('')

    await page.getByPlaceholder('Buscar número, cliente o NIF').fill(numero.replace(/^PRE-/, ''))
    await expect
      .poll(async () =>
        (await columna(page, COLUMNA.numero))
          .filter((n) => n.startsWith('PRE-'))
          .map((n) => /PRE-\d{4}-\d{4,}/.exec(n)?.[0]),
      )
      .toEqual([numero])

    await page
      .getByPlaceholder('Buscar número, cliente o NIF')
      .fill(sinTildes(cliente).toLowerCase())
    await expect
      .poll(async () => (await columna(page, COLUMNA.cliente)).every((c) => c === cliente))
      .toBe(true)

    await page.getByPlaceholder('Buscar número, cliente o NIF').fill('')
    const [fecha = ''] = await columna(page, COLUMNA.fecha)
    const mes = Number(fecha.split('/')[1])
    const nombreMes = new Intl.DateTimeFormat('es-ES', { month: 'long' }).format(
      new Date(2026, mes - 1, 1),
    )
    await elegir(page, /Mes/, nombreMes.charAt(0).toUpperCase() + nombreMes.slice(1))
    await expect(page).toHaveURL(new RegExp(`mes=${String(mes)}`))
    await expect
      .poll(async () =>
        (await columna(page, COLUMNA.fecha)).every((f) => Number(f.split('/')[1]) === mes),
      )
      .toBe(true)
  })

  test('orden por total y paginación, con el estado en la URL al recargar', async ({ page }) => {
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

    await siguientePagina(page)
    await expect.poll(async () => (await destinos(page))[0]).not.toBe(primeraPagina[0])
    const segundaPagina = await destinos(page)
    expect(segundaPagina.some((d) => primeraPagina.includes(d))).toBe(false)

    await page.reload()
    await expect(page.getByRole('button', { name: /Ordenar/ })).toContainText('Total mayor')
    expect(await destinos(page)).toEqual(segundaPagina)
  })

  test('«Imprimir listado» lleva el filtro de la pantalla, sin la página, y abre el PDF', async ({
    page,
  }) => {
    await elegir(page, /Ordenar/, 'Total menor')
    await siguientePagina(page)

    const imprimir = page.getByRole('link', { name: 'Imprimir listado' })
    await expect(imprimir).toHaveAttribute(
      'href',
      '/api/v1/presupuestos/listado/pdf?anio=todos&orden=total_asc',
    )
    await expect(imprimir).toHaveAttribute('target', '_blank')
    const respuesta = await page.request.get(
      '/api/v1/presupuestos/listado/pdf?anio=todos&orden=total_asc',
    )
    expect(respuesta.status()).toBe(200)
    expect(respuesta.headers()['content-disposition']).toBe(
      'inline; filename="presupuestos-todos.pdf"',
    )
    expect((await respuesta.body()).subarray(0, 4).toString()).toBe('%PDF')
  })
})
