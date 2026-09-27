import { expect, test, type Page } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'
import { dni, unico } from './helpers/entorno'

async function crearYAbrir(page: Page, nombre: string, nif: string) {
  await page.getByRole('link', { name: 'Nuevo cliente' }).first().click()
  await page.getByLabel(/Nombre o razón social/).fill(nombre)
  await page.getByLabel(/Número de identificación/).fill(nif)
  await page.getByRole('button', { name: 'Crear cliente' }).click()
  await expect(page.getByText(`Cliente «${nombre}» creado.`)).toBeVisible()
  await page.getByPlaceholder('Buscar nombre, NIF o localidad').fill(nif)
  const tabla = page.getByRole('table', { name: 'Listado de clientes' })
  await tabla.getByRole('link', { name: `Editar cliente ${nombre}` }).click()
  await expect(page.getByRole('dialog').getByRole('heading', { name: nombre })).toBeVisible()
}

test.describe('Ciclo de vida del cliente (US4)', () => {
  test('desactivar, encontrarlo con "Inactivos" y reactivar', async ({ page }) => {
    await iniciarSesion(page, 'empleado.demo')
    const numero = unico()
    const nombre = `Baja Temporal ${numero}`
    await crearYAbrir(page, nombre, dni(numero))

    await page.getByRole('button', { name: 'Desactivar cliente' }).click()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Desactivar' }).click()
    await expect(page.getByText('Cliente desactivado.')).toBeVisible()
    await expect(page.getByRole('alertdialog')).toHaveCount(0)
    await page.getByRole('button', { name: 'Cerrar panel' }).click()

    const tabla = page.getByRole('table', { name: 'Listado de clientes' })
    await expect(page.getByText('No hay resultados')).toBeVisible()
    await page.getByRole('button', { name: /Estado/ }).click()
    await page.getByRole('option', { name: 'Inactivos' }).click()
    await expect(tabla.getByText(nombre)).toBeVisible()
    await expect(tabla.getByText('Inactivo')).toBeVisible()

    await tabla.getByRole('link', { name: `Editar cliente ${nombre}` }).click()
    await page.getByRole('button', { name: 'Reactivar cliente' }).click()
    await expect(page.getByText('Cliente reactivado.')).toBeVisible()
  })

  test('el administrador borra con confirmación reforzada; el empleado no ve la opción', async ({
    page,
    browser,
  }) => {
    await iniciarSesion(page, 'admin.demo')
    const numero = unico()
    const nif = dni(numero)
    const nombre = `Para Borrar ${numero}`
    await crearYAbrir(page, nombre, nif)
    const url = page.url()

    const empleado = await browser.newPage()
    await iniciarSesion(empleado, 'empleado.demo')
    await empleado.goto(url)
    await expect(empleado.getByRole('button', { name: 'Desactivar cliente' })).toBeVisible()
    await expect(empleado.getByRole('button', { name: 'Borrar definitivamente' })).toHaveCount(0)
    await empleado.close()

    await page.getByRole('button', { name: 'Borrar definitivamente' }).click()
    const dialogo = page.getByRole('alertdialog', { name: 'Borrar definitivamente' })
    await expect(dialogo.getByRole('button', { name: 'Borrar' })).toBeDisabled()
    await dialogo.getByLabel(/Escribe la identificación/).fill(nif)
    await dialogo.getByRole('button', { name: 'Borrar' }).click()

    await expect(page.getByText('Cliente borrado.')).toBeVisible()
    await expect(page).toHaveURL(/\/clientes(\?|$)/)
    await expect(page.getByText('No hay resultados')).toBeVisible()
  })
})
