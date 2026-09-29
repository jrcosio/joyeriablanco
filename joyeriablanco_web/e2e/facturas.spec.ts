import { expect, test } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'
import { dni, unico } from './helpers/entorno'

interface FacturaCreada {
  id: string
  num_serie: string
}

test.describe('Facturas', () => {
  test('emitir una factura de dos líneas con un cliente dado de alta desde el modal y encontrarla en el listado (US2, US3)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'empleado.demo')
    await page.getByRole('link', { name: 'Facturas' }).click()
    await page.getByRole('link', { name: 'Nueva factura' }).click()

    const modal = page.getByRole('dialog', { name: 'Nueva factura' })
    await expect(modal.getByText('Se asigna al emitir')).toBeVisible()
    const previsto = (await modal.getByText(/^Previsto:/).textContent()) ?? ''
    const [numeroPrevisto = ''] = /FAC-\d{4}-\d{4,}/.exec(previsto) ?? []
    expect(numeroPrevisto).not.toBe('')

    // Primera línea antes de elegir cliente: debe seguir ahí al volver del alta.
    await modal.getByRole('textbox', { name: 'Descripción de la línea 1' }).fill('Anillo')
    await modal
      .getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' })
      .fill('1.200')

    // «Nuevo cliente» desde el modal (FR-046).
    const numero = unico()
    const nombre = `Cliente Factura ${numero}`
    await modal.getByRole('button', { name: 'Nuevo cliente' }).click()
    const alta = page.getByRole('dialog', { name: 'Nuevo cliente' })
    await alta.getByLabel(/Nombre o razón social/).fill(nombre)
    await alta.getByLabel(/Número de identificación/).fill(dni(numero))
    await alta.getByLabel('Dirección').fill('Calle Recogidas, 12')
    await alta.getByLabel('Código postal').fill('18005')
    await alta.getByLabel('Localidad').fill('Granada')
    await alta.getByRole('button', { name: 'Crear cliente' }).click()
    await expect(alta).toHaveCount(0)

    await expect(modal.getByRole('combobox', { name: /Cliente/ })).toHaveValue(
      `${nombre} · ${dni(numero)}`,
    )
    await expect(modal.getByText('Calle Recogidas, 12')).toBeVisible()
    await expect(modal.getByRole('textbox', { name: 'Descripción de la línea 1' })).toHaveValue(
      'Anillo',
    )

    // Segunda línea y previsualización de la captura.
    await modal.getByRole('button', { name: 'Añadir línea' }).click()
    await modal.getByRole('textbox', { name: 'Unidades de la línea 2' }).fill('2')
    await modal.getByRole('textbox', { name: 'Descripción de la línea 2' }).fill('Ajuste')
    await modal.getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 2' }).fill('45')
    await expect(modal.getByText('1.560,90 €')).toBeVisible()

    // Emitir con confirmación.
    const respuesta = page.waitForResponse(
      (r) => r.url().endsWith('/api/v1/facturas') && r.request().method() === 'POST',
    )
    await modal.getByRole('button', { name: 'Emitir factura' }).click()
    await page
      .getByRole('alertdialog', { name: '¿Emitir la factura?' })
      .getByRole('button', { name: 'Emitir factura' })
      .click()
    const creada = (await (await respuesta).json()) as FacturaCreada
    expect(creada.num_serie).toBe(numeroPrevisto)
    await expect(page.getByText(`Factura ${creada.num_serie} emitida`)).toBeVisible()
    await expect(modal).toHaveCount(0)
    await expect(page).toHaveURL(/\/facturas(\?|$)/)

    // Listado (US3): la búsqueda por el NIF con separadores la encuentra.
    const nif = dni(numero)
    await page
      .getByPlaceholder('Buscar número, cliente o NIF')
      .fill(`${nif.slice(0, 2)}.${nif.slice(2, 5)}.${nif.slice(5, 8)}-${nif.slice(8)}`)
    const tabla = page.getByRole('table', { name: 'Listado de facturas' })
    await expect(tabla.getByRole('row')).toHaveCount(2)
    await expect(tabla.getByText(creada.num_serie)).toBeVisible()
    await expect(tabla.getByText(nombre)).toBeVisible()
    await expect(page).toHaveURL(/q=/)

    // Detalle: datos del destinatario, importes del servidor y registro de alta con su huella.
    await page.goto(`/facturas/${creada.id}`)
    const detalle = page.getByRole('dialog', { name: `Factura ${creada.num_serie}` })
    await expect(detalle.getByText(nombre)).toBeVisible()
    await expect(detalle.getByText('1.290,00 €')).toBeVisible()
    await expect(detalle.getByText('270,90 €')).toBeVisible()
    await expect(detalle.getByText('1.560,90 €')).toBeVisible()
    await expect(detalle.getByText(/Registro de alta nº \d+/)).toBeVisible()
    await expect(detalle.getByText(/Huella [0-9A-F]{16}…/)).toBeVisible()
  })
})
