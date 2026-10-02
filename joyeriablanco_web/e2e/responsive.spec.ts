import { expect, test, type Page } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'

const ANCHOS = [360, 768, 1440] as const

async function sinDesplazamientoHorizontal(page: Page) {
  const { scroll, ventana } = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    ventana: window.innerWidth,
  }))
  expect(scroll, `desplazamiento horizontal a ${ventana}px`).toBeLessThanOrEqual(ventana)
}

for (const ancho of ANCHOS) {
  test(`sin desplazamiento horizontal a ${ancho}px (SC-008, FR-040, FR-059)`, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: 900 })

    await page.goto('/acceso')
    await expect(page.getByRole('button', { name: 'Entrar' })).toBeVisible()
    await sinDesplazamientoHorizontal(page)

    await iniciarSesion(page, 'admin.demo')
    await expect(page.getByRole('heading', { name: 'Clientes' })).toBeVisible()
    await sinDesplazamientoHorizontal(page)

    const cajon = page.getByRole('button', { name: 'Abrir menú de navegación' })
    if (ancho < 1024) {
      await expect(cajon).toBeVisible()
      await cajon.click()
      await expect(page.getByRole('dialog', { name: 'Navegación' })).toBeVisible()
      await page.getByRole('button', { name: 'Cerrar menú de navegación' }).click()
    } else {
      await expect(cajon).toBeHidden()
      await expect(page.getByRole('navigation', { name: 'Navegación principal' })).toBeVisible()
    }

    if (ancho < 768) {
      await expect(page.getByRole('list', { name: 'Listado de clientes' })).toBeVisible()
    } else {
      await expect(page.getByRole('table', { name: 'Listado de clientes' })).toBeVisible()
    }

    await page.getByRole('link', { name: 'Nuevo cliente' }).first().click()
    await expect(page.getByRole('heading', { name: 'Nuevo cliente' })).toBeVisible()
    await sinDesplazamientoHorizontal(page)
    await page.getByRole('button', { name: 'Cerrar panel' }).click()

    await page.goto('/configuracion/usuarios')
    await expect(page.getByRole('table', { name: 'Usuarios del sistema' })).toBeVisible()
    await sinDesplazamientoHorizontal(page)

    // Facturas (002, SC-008): listado y modal sin desplazamiento; modal a pantalla completa en
    // móvil y centrado desde 768 px.
    await page.goto('/facturas?anio=todos')
    await expect(
      page.getByRole(ancho < 768 ? 'list' : 'table', { name: 'Listado de facturas' }),
    ).toBeVisible()
    await sinDesplazamientoHorizontal(page)
    await page.goto('/facturas/nueva')
    const modal = page.getByRole('dialog', { name: 'Nueva factura' })
    await expect(modal.getByText('Se asigna al emitir')).toBeVisible()
    await sinDesplazamientoHorizontal(page)
    // Con la casilla de oro de inversión y su mención, tampoco (FR-040, FR-052).
    await modal.locator('label', { hasText: 'Sin IVA (oro de inversión)' }).click()
    await expect(modal.getByText(/Operación exenta de IVA/)).toBeVisible()
    await sinDesplazamientoHorizontal(page)
    const caja = await modal.boundingBox()
    expect(caja).not.toBeNull()
    if (ancho < 768) {
      expect(caja?.width).toBe(ancho)
      expect(caja?.x).toBe(0)
    } else {
      expect(caja?.width ?? 0).toBeLessThan(ancho)
    }

    // Presupuestos (005, SC-009): listado, modal nuevo y consulta con sus acciones.
    await page.goto('/presupuestos?anio=todos')
    await expect(
      page.getByRole(ancho < 768 ? 'list' : 'table', { name: 'Listado de presupuestos' }),
    ).toBeVisible()
    await sinDesplazamientoHorizontal(page)
    await page.goto('/presupuestos/nuevo')
    const nuevo = page.getByRole('dialog', { name: 'Nuevo presupuesto' })
    await expect(nuevo.getByText('Se asigna al emitir')).toBeVisible()
    await expect(nuevo.getByLabel(/Válido hasta/)).toBeVisible()
    await sinDesplazamientoHorizontal(page)
    const cajaPresupuesto = await nuevo.boundingBox()
    if (ancho < 768) expect(cajaPresupuesto?.width).toBe(ancho)
    await page.goto('/presupuestos?anio=todos')
    const ver = page.getByRole('link', { name: /^Ver presupuesto / }).first()
    await ver.click()
    const consulta = page.getByRole('dialog', { name: /^Presupuesto PRE-/ })
    await expect(consulta.getByRole('link', { name: /^Imprimir presupuesto / })).toBeVisible()
    await sinDesplazamientoHorizontal(page)
  })
}
