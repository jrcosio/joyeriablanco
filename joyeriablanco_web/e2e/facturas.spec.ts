import { expect, test, type Locator, type Page } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'
import { dni, unico } from './helpers/entorno'

interface FacturaCreada {
  id: string
  num_serie: string
}

/** Da de alta desde el modal un cliente facturable con nombre único y lo deja elegido. */
async function nuevoClienteDesdeElModal(page: Page, modal: Locator, prefijo: string) {
  const numero = unico()
  const nombre = `${prefijo} ${String(numero)}`
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
  return { nombre, numero }
}

async function previsto(modal: Locator): Promise<string> {
  await expect(modal.getByText('Se asigna al emitir')).toBeVisible()
  const texto = (await modal.getByText(/^Previsto:/).textContent()) ?? ''
  return /FAC-\d{4}-\d{4,}/.exec(texto)?.[0] ?? ''
}

test.describe('Facturas', () => {
  test('emitir una factura de dos líneas con un cliente dado de alta desde el modal y encontrarla en el listado (US2, US3)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'empleado.demo')
    await page.getByRole('link', { name: 'Facturas' }).click()
    await page.getByRole('link', { name: 'Nueva factura' }).click()

    const modal = page.getByRole('dialog', { name: 'Nueva factura' })
    const numeroPrevisto = await previsto(modal)
    expect(numeroPrevisto).not.toBe('')

    // Primera línea antes de elegir cliente: debe seguir ahí al volver del alta.
    await modal.getByRole('textbox', { name: 'Descripción de la línea 1' }).fill('Anillo')
    await modal
      .getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' })
      .fill('1.200')

    // «Nuevo cliente» desde el modal (FR-046): vuelve con el cliente elegido.
    const { nombre, numero } = await nuevoClienteDesdeElModal(page, modal, 'Cliente Factura')
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

  test('borrador: guardar, reabrirlo desde el listado, editarlo y emitirlo (US4)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'empleado.demo')
    await page.goto('/facturas/nueva')
    const nueva = page.getByRole('dialog', { name: 'Nueva factura' })
    await expect(nueva.getByText('Se asigna al emitir')).toBeVisible()
    const { nombre } = await nuevoClienteDesdeElModal(page, nueva, 'Cliente Borrador')
    await nueva.getByRole('textbox', { name: 'Descripción de la línea 1' }).fill('Collar')
    await nueva.getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' }).fill('300')

    await nueva.getByRole('button', { name: 'Guardar borrador' }).click()
    await expect(page.getByText('Borrador guardado')).toBeVisible()
    const borrador = page.getByRole('dialog', { name: 'Borrador' })
    await expect(borrador.getByRole('button', { name: 'Eliminar borrador' })).toBeVisible()
    await expect(page).toHaveURL(/\/facturas\/borradores\//)
    await borrador.getByRole('button', { name: 'Cancelar' }).click()
    await expect(borrador).toHaveCount(0)

    // Se reabre desde el listado, donde aparece marcado como borrador.
    await page.getByPlaceholder('Buscar número, cliente o NIF').fill(nombre)
    const tabla = page.getByRole('table', { name: 'Listado de facturas' })
    await expect(tabla.getByRole('row')).toHaveCount(2)
    await expect(tabla.getByText('Borrador', { exact: true })).toBeVisible()
    await tabla.getByRole('link', { name: `Abrir borrador de ${nombre}` }).click()
    await expect(
      borrador.getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' }),
    ).toHaveValue('300,00')

    // Se edita, se guarda y se emite.
    await borrador
      .getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' })
      .fill('1.200')
    await borrador.getByRole('button', { name: 'Guardar borrador' }).click()
    await expect(page.getByText('Borrador guardado')).toBeVisible()
    await expect(borrador.getByText('1.452,00 €')).toBeVisible()
    const numero = await previsto(borrador)
    await borrador.getByRole('button', { name: 'Emitir factura' }).click()
    await page
      .getByRole('alertdialog', { name: '¿Emitir la factura?' })
      .getByRole('button', { name: 'Emitir factura' })
      .click()
    await expect(page.getByText(`Factura ${numero} emitida`)).toBeVisible()
    await expect(borrador).toHaveCount(0)

    // En el listado ya no está el borrador sino la factura.
    await expect(tabla.getByText(numero)).toBeVisible()
    await expect(tabla.getByText('Borrador', { exact: true })).toHaveCount(0)
  })

  test('eliminar un borrador no consume número (US4, FR-019)', async ({ page }) => {
    await iniciarSesion(page, 'empleado.demo')
    await page.goto('/facturas/nueva')
    const nueva = page.getByRole('dialog', { name: 'Nueva factura' })
    const antes = await previsto(nueva)
    await nueva.getByRole('textbox', { name: 'Descripción de la línea 1' }).fill('Para borrar')
    await nueva.getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' }).fill('10')
    await nueva.getByRole('button', { name: 'Guardar borrador' }).click()

    const borrador = page.getByRole('dialog', { name: 'Borrador' })
    await borrador.getByRole('button', { name: 'Eliminar borrador' }).click()
    const confirmar = page.getByRole('alertdialog', { name: '¿Eliminar el borrador?' })
    await confirmar.getByRole('button', { name: 'Eliminar borrador' }).click()
    await expect(page.getByText('Borrador eliminado')).toBeVisible()
    await expect(borrador).toHaveCount(0)

    await page.getByRole('link', { name: 'Nueva factura' }).click()
    expect(await previsto(page.getByRole('dialog', { name: 'Nueva factura' }))).toBe(antes)
  })
})
