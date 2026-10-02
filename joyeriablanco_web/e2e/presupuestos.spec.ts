import { expect, test, type Locator, type Page } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'
import { dni, unico } from './helpers/entorno'
import { emitirPresupuestoPorLaApi, type PresupuestoCreado } from './helpers/presupuestos'

/** Da de alta desde el modal un cliente con nombre único y lo deja elegido. */
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
  return { nombre, numero }
}

async function previsto(modal: Locator): Promise<string> {
  await expect(modal.getByText('Se asigna al emitir')).toBeVisible()
  const texto = (await modal.getByText(/^Previsto:/).textContent()) ?? ''
  return /PRE-\d{4}-\d{4,}/.exec(texto)?.[0] ?? ''
}

test.describe('Presupuestos (005)', () => {
  test('borrador, edición y emisión con número PRE; el emitido ya no se edita (US1)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'empleado.demo')
    await page
      .getByRole('navigation', { name: 'Navegación principal' })
      .getByRole('link', { name: 'Presupuestos' })
      .click()
    await expect(page.getByRole('heading', { name: 'Presupuestos' })).toBeVisible()
    await page.getByRole('link', { name: 'Nuevo presupuesto' }).click()

    const modal = page.getByRole('dialog', { name: 'Nuevo presupuesto' })
    const numeroPrevisto = await previsto(modal)
    expect(numeroPrevisto).not.toBe('')
    await expect(modal.getByLabel(/Válido hasta/)).not.toHaveValue('')

    await modal.getByRole('textbox', { name: 'Descripción de la línea 1' }).fill('Anillo a medida')
    await modal
      .getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' })
      .fill('1.200')
    const { nombre } = await nuevoClienteDesdeElModal(page, modal, 'Cliente Presupuesto')
    await expect(modal.getByText('1.452,00 €')).toBeVisible()

    // Guardar borrador: el modal pasa al modo borrador.
    await modal.getByRole('button', { name: 'Guardar borrador' }).click()
    const borrador = page.getByRole('dialog', { name: 'Borrador de presupuesto' })
    await expect(borrador.getByRole('button', { name: 'Eliminar borrador' })).toBeVisible()

    // Editar y emitir con confirmación.
    await borrador.getByRole('textbox', { name: 'Unidades de la línea 1' }).fill('2')
    const respuesta = page.waitForResponse(
      (r) => r.url().includes('/api/v1/borradores-presupuesto/') && r.url().endsWith('/emision'),
    )
    await borrador.getByRole('button', { name: 'Emitir presupuesto' }).click()
    await page
      .getByRole('alertdialog', { name: '¿Emitir el presupuesto?' })
      .getByRole('button', { name: 'Emitir presupuesto' })
      .click()
    const creado = (await (await respuesta).json()) as PresupuestoCreado
    expect(creado.num_serie).toBe(numeroPrevisto)
    await expect(page.getByText(`Presupuesto ${creado.num_serie} emitido`)).toBeVisible()

    // Listado: búsqueda por el cliente.
    await page.getByPlaceholder('Buscar número, cliente o NIF').fill(nombre)
    const tabla = page.getByRole('table', { name: 'Listado de presupuestos' })
    await expect(tabla.getByText(creado.num_serie)).toBeVisible()

    // Consulta: nada editable, con sus importes.
    await tabla.getByRole('link', { name: `Ver presupuesto ${creado.num_serie}` }).click()
    const consulta = page.getByRole('dialog', { name: `Presupuesto ${creado.num_serie}` })
    await expect(consulta.getByText('2.904,00 €')).toBeVisible()
    await expect(consulta.getByRole('textbox')).toHaveCount(0)
  })

  test('eliminar un borrador no consume número (US1, FR-012)', async ({ page }) => {
    await iniciarSesion(page, 'empleado.demo')
    await page.goto('/presupuestos/nuevo')
    const modal = page.getByRole('dialog', { name: 'Nuevo presupuesto' })
    const numeroPrevisto = await previsto(modal)
    await modal.getByRole('button', { name: 'Quitar la línea 1' }).click()
    await modal.getByRole('button', { name: 'Guardar borrador' }).click()

    const borrador = page.getByRole('dialog', { name: 'Borrador de presupuesto' })
    await borrador.getByRole('button', { name: 'Eliminar borrador' }).click()
    await page
      .getByRole('alertdialog', { name: '¿Eliminar el borrador?' })
      .getByRole('button', { name: 'Eliminar borrador' })
      .click()
    await expect(page.getByText('Borrador eliminado')).toBeVisible()

    await page.goto('/presupuestos/nuevo')
    expect(await previsto(page.getByRole('dialog', { name: 'Nuevo presupuesto' }))).toBe(
      numeroPrevisto,
    )
  })

  test('un presupuesto emitido por la API aparece en el listado con su número (US1)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'empleado.demo')
    await page.goto('/presupuestos')
    const presupuesto = await emitirPresupuestoPorLaApi(page)

    await page.getByPlaceholder('Buscar número, cliente o NIF').fill(presupuesto.num_serie)
    const tabla = page.getByRole('table', { name: 'Listado de presupuestos' })
    await expect(tabla.getByText(presupuesto.num_serie)).toBeVisible()
    await expect(tabla.getByText(presupuesto.cliente)).toBeVisible()
  })
})
