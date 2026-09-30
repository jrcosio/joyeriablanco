import { expect, test, type Page } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'
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
  // La URL cambia antes de que se pinte la pantalla: se tabula cuando ya está.
  await expect(page.getByRole('heading', { name: 'Clientes', level: 1 })).toBeVisible()

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

/** Nombre accesible del elemento con el foco: `aria-label`, su `<label>` o su texto. */
async function nombreDelFoco(page: Page): Promise<string> {
  return page.evaluate(() => {
    const activo = document.activeElement as HTMLInputElement | null
    return (
      activo?.getAttribute('aria-label') ??
      activo?.labels?.[0]?.textContent ??
      activo?.textContent ??
      ''
    ).trim()
  })
}

async function tabularHastaNombre(page: Page, nombre: RegExp, maximo = 60) {
  for (let i = 0; i < maximo; i++) {
    await page.keyboard.press('Tab')
    if (nombre.test(await nombreDelFoco(page))) return
  }
  throw new Error(`No se ha llegado con el tabulador a ${String(nombre)}`)
}

test('modal de factura solo con teclado: dos capas, Escape y foco devuelto (FR-039, FR-046)', async ({
  page,
}) => {
  await iniciarSesion(page, 'empleado.demo')
  await page.goto('/facturas')
  await expect(page.getByRole('table', { name: 'Listado de facturas' })).toBeVisible()

  await tabularHastaNombre(page, /^Nueva factura$/)
  expect(await focoVisible(page)).toBe(true)
  await page.keyboard.press('Enter')
  const modal = page.getByRole('dialog', { name: 'Nueva factura' })
  await expect(modal.getByText('Se asigna al emitir')).toBeVisible()

  // Segunda capa: alta de cliente por encima; Escape cierra solo esa y el foco vuelve.
  await tabularHastaNombre(page, /^Nuevo cliente$/)
  await page.keyboard.press('Enter')
  const alta = page.getByRole('dialog', { name: 'Nuevo cliente' })
  await expect(alta).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(alta).toHaveCount(0)
  await expect(modal).toBeVisible()
  await expect.poll(() => nombreDelFoco(page)).toBe('Nuevo cliente')

  // Una línea escrita con el teclado; el foco no sale del modal.
  await tabularHastaNombre(page, /^Descripción de la línea 1/)
  await page.keyboard.type('Anillo')
  expect(
    await page.evaluate(() => document.activeElement?.closest('[role="dialog"]') !== null),
  ).toBe(true)

  // Tras «Añadir línea» llega la casilla «Sin IVA (oro de inversión)» (ui-rutas); se marca con la
  // barra espaciadora.
  await tabularHastaNombre(page, /^Añadir línea$/, 10)
  await tabularHastaNombre(page, /^Sin IVA \(oro de inversión\)$/, 3)
  await page.keyboard.press('Space')
  await expect(modal.getByRole('checkbox', { name: 'Sin IVA (oro de inversión)' })).toBeChecked()
  await expect(modal.getByText('Base exenta')).toBeVisible()

  // Escape con cambios pide confirmación; se descarta con el teclado y el foco vuelve al botón.
  await page.keyboard.press('Escape')
  const descartar = page.getByRole('alertdialog', { name: '¿Descartar los cambios?' })
  await expect(descartar).toBeVisible()
  await tabularHastaNombre(page, /^Descartar$/, 5)
  await page.keyboard.press('Enter')
  await expect(modal).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'Nueva factura' })).toBeFocused()
})
