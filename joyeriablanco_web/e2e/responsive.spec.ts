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
  })
}
