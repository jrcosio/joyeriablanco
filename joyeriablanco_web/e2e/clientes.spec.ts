import { expect, test, type Page } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'
import { dni, unico } from './helpers/entorno'

function panel(page: Page) {
  return page.getByRole('dialog')
}

async function abrirAlta(page: Page) {
  await page.getByRole('link', { name: 'Nuevo cliente' }).first().click()
  await expect(page.getByRole('heading', { name: 'Nuevo cliente' })).toBeVisible()
}

async function crearCliente(page: Page, nombre: string, nif: string, cp = '29005') {
  await abrirAlta(page)
  await page.getByLabel(/Nombre o razón social/).fill(nombre)
  await page.getByLabel(/Número de identificación/).fill(nif)
  await page.getByLabel('Código postal').fill(cp)
  await page.getByRole('button', { name: 'Crear cliente' }).click()
  await expect(page.getByText(`Cliente «${nombre}» creado.`)).toBeVisible()
}

test.describe('Clientes (US2 y US3)', () => {
  test.beforeEach(async ({ page }) => {
    await iniciarSesion(page, 'empleado.demo')
  })

  test('alta con NIF: rechaza la letra incorrecta y deduce la provincia del CP', async ({
    page,
  }) => {
    const numero = unico()
    const correcto = dni(numero)
    const incorrecto = `${correcto.slice(0, 8)}${correcto.endsWith('A') ? 'B' : 'A'}`
    await abrirAlta(page)
    await page.getByLabel(/Nombre o razón social/).fill(`María López García ${numero}`)
    await page.getByLabel(/Número de identificación/).fill(incorrecto)
    await page.getByLabel('Código postal').fill('29005')
    await expect(panel(page).getByRole('button', { name: /Provincia/ })).toContainText('Málaga')

    await page.getByRole('button', { name: 'Crear cliente' }).click()
    await expect(page.getByText('La letra del NIF no es correcta.')).toBeVisible()

    await page.getByLabel(/Número de identificación/).fill(correcto)
    await page.getByRole('button', { name: 'Crear cliente' }).click()
    await expect(page.getByText(`Cliente «María López García ${numero}» creado.`)).toBeVisible()
    await expect(page).toHaveURL(/\/clientes(\?|$)/)
  })

  test('búsqueda sin tildes ni mayúsculas y edición del cliente', async ({ page }) => {
    const numero = unico()
    await crearCliente(page, `Ángela Núñez ${numero}`, dni(numero))

    await page.getByPlaceholder('Buscar nombre, NIF o localidad').fill(`angela nunez ${numero}`)
    const tabla = page.getByRole('table', { name: 'Listado de clientes' })
    await expect(tabla.getByText(`Ángela Núñez ${numero}`)).toBeVisible()
    await expect(page).toHaveURL(new RegExp(`q=angela`))

    await tabla.getByRole('link', { name: `Editar cliente Ángela Núñez ${numero}` }).click()
    await expect(panel(page).getByRole('heading', { name: `Ángela Núñez ${numero}` })).toBeVisible()
    await panel(page).getByLabel('Localidad', { exact: true }).fill('Ronda')
    await page.getByRole('button', { name: 'Guardar cambios' }).click()
    await expect(page.getByText('Cambios guardados.')).toBeVisible()
    await expect(tabla.getByText('Ronda')).toBeVisible()
  })

  test('filtros y orden', async ({ page }) => {
    await page.getByRole('button', { name: /Tipo/ }).click()
    const conTipo = page.waitForResponse((r) => r.url().includes('tipo=empresa'))
    await page.getByRole('option', { name: 'Empresas' }).click()
    await conTipo
    await expect(page).toHaveURL(/tipo=empresa/)

    const tabla = page.getByRole('table', { name: 'Listado de clientes' })
    await expect(tabla.locator('tbody tr').first()).toBeVisible()
    const tipos = await tabla.locator('tbody tr td:first-child .label-sm').allTextContents()
    expect(tipos.every((t) => t.toLowerCase() === 'empresa')).toBe(true)

    await page.getByRole('button', { name: /Ordenar/ }).click()
    const conOrden = page.waitForResponse((r) => r.url().includes('orden=nombre_desc'))
    await page.getByRole('option', { name: 'Nombre (Z–A)' }).click()
    await conOrden
    await expect(page).toHaveURL(/orden=nombre_desc/)
    await expect(tabla.locator('tbody tr td:first-child .title-md').first()).toBeVisible()
    const nombres = await tabla.locator('tbody tr td:first-child .title-md').allTextContents()
    const colacion = new Intl.Collator('es', { sensitivity: 'base', ignorePunctuation: true })
    const ordenados = [...nombres].sort((a, b) => colacion.compare(b, a))
    expect(nombres).toEqual(ordenados)
  })

  test('conflicto de versión entre dos usuarios que editan a la vez', async ({ page, browser }) => {
    const numero = unico()
    const nombre = `Conflicto ${numero}`
    await crearCliente(page, nombre, dni(numero))
    await page.getByPlaceholder('Buscar nombre, NIF o localidad').fill(String(numero))
    const tabla = page.getByRole('table', { name: 'Listado de clientes' })
    await tabla.getByRole('link', { name: `Editar cliente ${nombre}` }).click()
    await expect(panel(page).getByRole('heading', { name: nombre })).toBeVisible()
    const url = page.url()

    const otro = await browser.newPage()
    await iniciarSesion(otro, 'admin.demo')
    await otro.goto(url)
    await expect(panel(otro).getByRole('heading', { name: nombre })).toBeVisible()
    await panel(otro).getByLabel('Localidad', { exact: true }).fill('Nerja')
    await otro.getByRole('button', { name: 'Guardar cambios' }).click()
    await expect(otro.getByText('Cambios guardados.')).toBeVisible()
    await otro.close()

    await panel(page).getByLabel('Localidad', { exact: true }).fill('Antequera')
    await page.getByRole('button', { name: 'Guardar cambios' }).click()
    await expect(page.getByRole('alertdialog', { name: 'El cliente ha cambiado' })).toBeVisible()
  })
})
