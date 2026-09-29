import { expect, test, type Locator, type Page } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'

/**
 * La acción de cada fila se ve sin buscar, filtrar ni desplazar (FR-031, FR-059, SC-014, R-22).
 * jsdom no maqueta: el recorte de la columna de acciones solo se detecta en un navegador real.
 */

const ANCHOS = [360, 768, 1024, 1280, 1440] as const
/** Clientes añade 1536 px, desde donde se muestran teléfono y correo (FR-059). */
const ANCHOS_CLIENTES = [...ANCHOS, 1536] as const

/** Anchos de SC-008 de 002 para la tabla de facturas (más 360 px, con tarjetas). */
const ANCHOS_FACTURAS = [360, 768, 1024, 1280, 1440, 1536] as const

/** Columnas de la tabla de facturas según el ancho, medidas como en 001 R-22 (002, T056). */
function columnasFacturas(ancho: number) {
  return {
    'NIF/CIF': ancho >= 1280,
    'Base imponible': ancho >= 1440,
    IVA: ancho >= 1440,
  }
}

/** Columnas de la tabla de clientes según el ancho (FR-059, R-22). */
function columnasVisibles(ancho: number) {
  return {
    Provincia: ancho < 1024 || ancho >= 1280,
    Teléfono: ancho >= 1536,
    Correo: ancho >= 1536,
  }
}

interface Medida {
  total: number
  cortadas: string[]
  tapadas: string[]
  fondos: string[]
  desplazados: number
}

/**
 * Mide cada acción sin desplazar nada en horizontal:
 * - Su rectángulo queda dentro de la ventana y de todos sus ancestros que recortan.
 * - En su centro no hay otro elemento encima.
 * - En tablas, la celda fija tiene un fondo opaco igual al de la tarjeta y la cabecera fija el del
 *   `thead`.
 */
async function medirAcciones(acciones: Locator, enTabla: boolean): Promise<Medida> {
  return acciones.evaluateAll((elementos, enTabla) => {
    const opaco = (color: string) => color !== '' && color !== 'rgba(0, 0, 0, 0)'
    const fondoDe = (desde: Element | null) => {
      for (let el = desde; el; el = el.parentElement) {
        const color = getComputedStyle(el).backgroundColor
        if (opaco(color)) return color
      }
      return ''
    }
    const nombre = (el: Element) => el.getAttribute('aria-label') ?? ''
    const cortadas: string[] = []
    const tapadas: string[] = []
    const fondos: string[] = []

    for (const el of elementos) {
      const r = el.getBoundingClientRect()
      let dentro = r.left >= 0 && r.right <= window.innerWidth
      for (let a = el.parentElement; a; a = a.parentElement) {
        if (getComputedStyle(a).overflowX === 'visible') continue
        const c = a.getBoundingClientRect()
        if (r.left < c.left - 0.5 || r.right > c.right + 0.5) dentro = false
      }
      if (!dentro) cortadas.push(nombre(el))

      window.scrollTo({ top: window.scrollY + r.top - window.innerHeight / 2, behavior: 'instant' })
      const v = el.getBoundingClientRect()
      const encima = document.elementFromPoint(v.left + v.width / 2, v.top + v.height / 2)
      if (!encima || !el.contains(encima)) tapadas.push(nombre(el))

      if (enTabla) {
        const celda = el.closest('td')
        const tabla = el.closest('table')
        const esperado = fondoDe(tabla?.parentElement ?? null)
        const real = celda ? getComputedStyle(celda).backgroundColor : ''
        if (!opaco(real) || real !== esperado) fondos.push(`${nombre(el)}: ${real} ≠ ${esperado}`)
      }
    }

    if (enTabla) {
      const tabla = elementos[0]?.closest('table')
      const cabecera = tabla?.querySelector('thead tr > th:last-child')
      const thead = tabla?.querySelector('thead') ?? null
      const real = cabecera ? getComputedStyle(cabecera).backgroundColor : ''
      const esperado = fondoDe(thead)
      if (!opaco(real) || real !== esperado) fondos.push(`cabecera: ${real} ≠ ${esperado}`)
    }

    const desplazados = [...document.querySelectorAll('*')].filter((e) => e.scrollLeft !== 0)
    return { total: elementos.length, cortadas, tapadas, fondos, desplazados: desplazados.length }
  }, enTabla)
}

async function esperarVisibles(page: Page, acciones: Locator, minimo: number, enTabla: boolean) {
  await expect(acciones.first()).toBeAttached()
  expect(await acciones.count()).toBeGreaterThanOrEqual(minimo)
  // El ratón en el margen izquierdo: ninguna fila queda en hover durante la medida. Se espera a
  // que acabe la transición de color de la fila que pudiera haber quedado en hover.
  await page.mouse.move(0, 0)
  await page.waitForFunction(() => document.getAnimations().length === 0)
  const medida = await medirAcciones(acciones, enTabla)
  expect(medida.cortadas, 'acciones recortadas').toEqual([])
  expect(medida.tapadas, 'acciones tapadas por otro elemento').toEqual([])
  expect(medida.fondos, 'fondo de la columna fija').toEqual([])
  expect(medida.desplazados, 'contenedores desplazados en horizontal').toBe(0)
  await page.evaluate(() => {
    window.scrollTo({ top: 0, behavior: 'instant' })
  })
}

async function sinDesplazamientoHorizontal(page: Page) {
  const { scroll, ventana } = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    ventana: window.innerWidth,
  }))
  expect(scroll, `desplazamiento horizontal a ${ventana}px`).toBeLessThanOrEqual(ventana)
}

test.describe('Acciones siempre visibles (SC-014, FR-031, FR-059)', () => {
  for (const ancho of ANCHOS_CLIENTES) {
    test(`clientes a ${ancho}px: el lápiz de cada fila sin buscar (US3-8)`, async ({ page }) => {
      await page.setViewportSize({ width: ancho, height: 900 })
      await iniciarSesion(page, 'admin.demo')

      if (ancho < 768) {
        const lista = page.getByRole('list', { name: 'Listado de clientes' })
        await expect(lista).toBeVisible()
        const editar = lista.getByRole('link', { name: /^Editar cliente / })
        await expect(editar).toHaveCount(25)
        await esperarVisibles(page, editar, 25, false)
        await sinDesplazamientoHorizontal(page)
        return
      }

      const tabla = page.getByRole('table', { name: 'Listado de clientes' })
      await expect(tabla).toBeVisible()
      const editar = tabla.getByRole('link', { name: /^Editar cliente / })
      await expect(editar).toHaveCount(25)
      await esperarVisibles(page, editar, 25, true)
      await sinDesplazamientoHorizontal(page)

      for (const [columna, visible] of Object.entries(columnasVisibles(ancho))) {
        const cabecera = tabla.getByRole('columnheader', { name: columna, exact: true })
        if (visible) await expect(cabecera, `${columna} a ${ancho}px`).toBeVisible()
        else await expect(cabecera, `${columna} a ${ancho}px`).toBeHidden()
      }

      const ultimo = editar.last()
      const etiqueta = (await ultimo.getAttribute('aria-label')) ?? ''
      await ultimo.click()
      await expect(
        page.getByRole('dialog').getByRole('heading', {
          name: etiqueta.replace(/^Editar cliente /, ''),
        }),
      ).toBeVisible()
    })
  }

  for (const ancho of ANCHOS) {
    test(`usuarios y auditoría a ${ancho}px: la acción de cada fila sin desplazar (US5-13)`, async ({
      page,
    }) => {
      await page.setViewportSize({ width: ancho, height: 900 })
      await iniciarSesion(page, 'admin.demo')

      await page.goto('/configuracion/usuarios')
      const usuarios = page.getByRole('table', { name: 'Usuarios del sistema' })
      await expect(usuarios).toBeVisible()
      const menus = usuarios.getByRole('button', { name: /^Acciones para / })
      await esperarVisibles(page, menus, 1, true)
      await sinDesplazamientoHorizontal(page)
      await menus.last().click()
      await expect(page.getByRole('menu')).toBeVisible()
      await page.keyboard.press('Escape')

      await page.goto('/configuracion/auditoria')
      const auditoria = page.getByRole('table', { name: 'Eventos de auditoría' })
      await expect(auditoria).toBeVisible()
      const detalles = auditoria.getByRole('button', { name: /^Ver detalle: / })
      await esperarVisibles(page, detalles, 1, true)
      await sinDesplazamientoHorizontal(page)
    })
  }

  for (const ancho of ANCHOS_FACTURAS) {
    test(`facturas a ${ancho}px: «Ver factura» en cada fila de una página completa (002, SC-008)`, async ({
      page,
    }) => {
      await page.setViewportSize({ width: ancho, height: 900 })
      await iniciarSesion(page, 'admin.demo')
      // Todos los años: los datos de ejemplo llenan más de una página (R-16).
      await page.goto('/facturas?anio=todos')

      if (ancho < 768) {
        const lista = page.getByRole('list', { name: 'Listado de facturas' })
        const ver = lista.getByRole('link', { name: /^Ver factura / })
        await expect(ver).toHaveCount(25)
        await esperarVisibles(page, ver, 25, false)
        await sinDesplazamientoHorizontal(page)
        return
      }

      const tabla = page.getByRole('table', { name: 'Listado de facturas' })
      const ver = tabla.getByRole('link', { name: /^Ver factura / })
      await expect(ver).toHaveCount(25)
      await esperarVisibles(page, ver, 25, true)
      await sinDesplazamientoHorizontal(page)
      for (const [columna, visible] of Object.entries(columnasFacturas(ancho))) {
        const cabecera = tabla.getByRole('columnheader', { name: columna, exact: true })
        if (visible) await expect(cabecera, `${columna} a ${ancho}px`).toBeVisible()
        else await expect(cabecera, `${columna} a ${ancho}px`).toBeHidden()
      }
      // Con las columnas visibles, la tabla cabe en su tarjeta sin desplazarse.
      const cabe = await tabla.evaluate(
        (t) => t.scrollWidth <= (t.parentElement?.clientWidth ?? 0) + 0.5,
      )
      expect(cabe, `la tabla de facturas cabe a ${ancho}px`).toBe(true)
    })
  }

  test('clientes con datos largos: la tabla se desplaza en su tarjeta y el lápiz sigue visible', async ({
    page,
  }) => {
    // Solo el listado (no los indicadores ni la ficha); sin tocar la BD de E2E.
    await page.route(
      (url) => url.pathname === '/api/v1/clientes',
      async (route) => {
        if (route.request().method() !== 'GET') {
          await route.continue()
          return
        }
        const respuesta = await route.fetch()
        const cuerpo = (await respuesta.json()) as { elementos: Record<string, unknown>[] }
        const primero = cuerpo.elementos.at(0)
        if (primero) {
          primero.nombre =
            `Aaa ${'Supercalifragilisticoespialidosamentes'.padEnd(40, 'x')} ${'Joyería '.repeat(9)}`
              .slice(0, 120)
              .trim()
          primero.localidad = 'Villanueva de la Cañada del Marquesado de las Altas Montañas'
          primero.correo = `${'direccion.de.correo.muy.larga.'.repeat(2)}ejemplo@example.com`
        }
        await route.fulfill({ response: respuesta, json: cuerpo })
      },
    )

    await page.setViewportSize({ width: 768, height: 900 })
    await iniciarSesion(page, 'admin.demo')
    const tabla = page.getByRole('table', { name: 'Listado de clientes' })
    await expect(tabla.getByText(/^Aaa Supercalifragilistico/)).toBeVisible()

    for (const ancho of ANCHOS_CLIENTES.filter((a) => a >= 768)) {
      await page.setViewportSize({ width: ancho, height: 900 })
      const editar = tabla.getByRole('link', { name: /^Editar cliente / })
      await expect(editar).toHaveCount(25)
      await esperarVisibles(page, editar, 25, true)
      await sinDesplazamientoHorizontal(page)
    }
  })
})
