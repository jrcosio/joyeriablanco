import { expect, test, type Page } from '@playwright/test'
import { CONTRASENA, dni, unico } from './helpers/entorno'

async function focoVisible(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    const activo = document.activeElement
    if (!activo || activo === document.body) return false
    const estilo = getComputedStyle(activo)
    return (
      estilo.outlineStyle !== 'none' || estilo.borderColor !== '' || estilo.boxShadow !== 'none'
    )
  })
}

async function tabularHasta(page: Page, nombre: RegExp, maximo = 40) {
  for (let i = 0; i < maximo; i++) {
    await page.keyboard.press('Tab')
    const etiqueta = await page.evaluate(() => {
      const activo = document.activeElement as HTMLElement | null
      return activo?.getAttribute('aria-label') ?? (activo?.textContent ?? '').trim()
    })
    if (nombre.test(etiqueta)) return
  }
  throw new Error(`No se ha llegado con el tabulador a ${String(nombre)}`)
}

test('recorrido completo solo con teclado: acceso y alta de cliente (FR-052)', async ({ page }) => {
  await page.goto('/acceso')
  await expect(page.getByLabel('Usuario')).toBeFocused() // autofoco
  await page.keyboard.type('empleado.demo')
  await page.keyboard.press('Tab')
  await page.keyboard.type(CONTRASENA)
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/clientes/)

  await tabularHasta(page, /Nuevo cliente/)
  expect(await focoVisible(page)).toBe(true)
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Nuevo cliente' })).toBeVisible()

  const numero = unico()
  await page.getByLabel(/Nombre o razón social/).focus()
  await page.keyboard.type(`Cliente Teclado ${numero}`)
  await page.getByLabel(/Número de identificación/).focus()
  await page.keyboard.type(dni(numero))
  await page.keyboard.press('Enter') // envío implícito del formulario

  await expect(page.getByText(`Cliente «Cliente Teclado ${numero}» creado.`)).toBeVisible()
})
