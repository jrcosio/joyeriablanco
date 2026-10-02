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

  test('imprimir un presupuesto desde su consulta abre su PDF (US2)', async ({ page }) => {
    await iniciarSesion(page, 'empleado.demo')
    await page.goto('/presupuestos')
    const presupuesto = await emitirPresupuestoPorLaApi(page)

    await page.goto(`/presupuestos/${presupuesto.id}`)
    const modal = page.getByRole('dialog', { name: `Presupuesto ${presupuesto.num_serie}` })
    const imprimir = modal.getByRole('link', {
      name: `Imprimir presupuesto ${presupuesto.num_serie}`,
    })
    await expect(imprimir).toHaveAttribute('target', '_blank')
    const base = `/api/v1/presupuestos/${presupuesto.id}/pdf`
    await expect(imprimir).toHaveAttribute('href', base)
    await expect(modal.getByRole('checkbox', { name: 'Duplicado' })).toHaveCount(0)

    // Con la sesión del navegador, sin depender del visor de PDF de Chromium (003, R-11).
    const respuesta = await page.request.get(base)
    expect(respuesta.status()).toBe(200)
    expect(respuesta.headers()['content-type']).toBe('application/pdf')
    expect(respuesta.headers()['content-disposition']).toBe(
      `inline; filename="${presupuesto.num_serie}.pdf"`,
    )
    expect((await respuesta.body()).subarray(0, 4).toString()).toBe('%PDF')
  })

  test('convertir en factura: borrador vinculado, en facturación y convertido (US3)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'empleado.demo')
    await page.goto('/presupuestos')
    const presupuesto = await emitirPresupuestoPorLaApi(page)

    // Convertir: el borrador de factura se abre con su origen.
    await page.goto(`/presupuestos/${presupuesto.id}`)
    let consulta = page.getByRole('dialog', { name: `Presupuesto ${presupuesto.num_serie}` })
    await consulta.getByRole('button', { name: 'Convertir en factura' }).click()
    await page
      .getByRole('alertdialog', { name: '¿Convertir en factura?' })
      .getByRole('button', { name: 'Convertir en factura' })
      .click()
    await expect(
      page.getByText(`Borrador de factura creado a partir de ${presupuesto.num_serie}`),
    ).toBeVisible()
    let borrador = page.getByRole('dialog', { name: 'Borrador' })
    await expect(borrador.getByText(/Procede del presupuesto/)).toBeVisible()
    await expect(page).toHaveURL(/\/facturas\/borradores\//)
    const urlBorrador = page.url()

    // De vuelta al presupuesto: en facturación, y «Abrir borrador» lleva al mismo.
    await borrador.getByRole('link', { name: presupuesto.num_serie }).click()
    consulta = page.getByRole('dialog', { name: `Presupuesto ${presupuesto.num_serie}` })
    await expect(
      consulta.getByText('Este presupuesto tiene un borrador de factura en curso.'),
    ).toBeVisible()
    await expect(consulta.getByRole('button', { name: 'Convertir en factura' })).toHaveCount(0)
    await consulta.getByRole('link', { name: 'Abrir borrador de factura' }).click()
    await expect(page).toHaveURL(urlBorrador)

    // Emitir: la factura enlaza con el presupuesto, que queda convertido en ella.
    borrador = page.getByRole('dialog', { name: 'Borrador' })
    const emision = page.waitForResponse(
      (r) => r.url().includes('/api/v1/borradores-factura/') && r.url().endsWith('/emision'),
    )
    await borrador.getByRole('button', { name: 'Emitir factura' }).click()
    await page
      .getByRole('alertdialog', { name: '¿Emitir la factura?' })
      .getByRole('button', { name: 'Emitir factura' })
      .click()
    const factura = (await (await emision).json()) as {
      id: string
      num_serie: string
      registros: { tipo: string }[]
    }
    expect(factura.num_serie).toMatch(/^FAC-\d{4}-\d{4,}$/)
    expect(factura.registros.map((r) => r.tipo)).toEqual(['alta'])
    await expect(
      page.getByText(
        `Factura ${factura.num_serie} emitida. ${presupuesto.num_serie} queda convertido`,
      ),
    ).toBeVisible()

    await page.goto(`/facturas/${factura.id}`)
    const consultaFactura = page.getByRole('dialog', { name: `Factura ${factura.num_serie}` })
    await consultaFactura.getByRole('link', { name: presupuesto.num_serie }).click()
    consulta = page.getByRole('dialog', { name: `Presupuesto ${presupuesto.num_serie}` })
    await expect(consulta.getByText('Convertido en factura')).toBeVisible()
    await expect(consulta.getByRole('link', { name: factura.num_serie })).toBeVisible()
    const pdf = await page.request.get(`/api/v1/presupuestos/${presupuesto.id}/pdf`)
    expect(pdf.status()).toBe(200)
  })

  test('eliminar el borrador de la conversión devuelve el presupuesto a pendiente (US3)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'empleado.demo')
    await page.goto('/presupuestos')
    const presupuesto = await emitirPresupuestoPorLaApi(page)

    await page.goto(`/presupuestos/${presupuesto.id}`)
    let consulta = page.getByRole('dialog', { name: `Presupuesto ${presupuesto.num_serie}` })
    await consulta.getByRole('button', { name: 'Convertir en factura' }).click()
    await page
      .getByRole('alertdialog', { name: '¿Convertir en factura?' })
      .getByRole('button', { name: 'Convertir en factura' })
      .click()
    const borrador = page.getByRole('dialog', { name: 'Borrador' })
    await borrador.getByRole('button', { name: 'Eliminar borrador' }).click()
    await page
      .getByRole('alertdialog', { name: '¿Eliminar el borrador?' })
      .getByRole('button', { name: 'Eliminar borrador' })
      .click()
    await expect(page.getByText('Borrador eliminado')).toBeVisible()

    await page.goto(`/presupuestos/${presupuesto.id}`)
    consulta = page.getByRole('dialog', { name: `Presupuesto ${presupuesto.num_serie}` })
    await expect(consulta.getByRole('button', { name: 'Convertir en factura' })).toBeVisible()
    await expect(
      consulta.getByText('Este presupuesto tiene un borrador de factura en curso.'),
    ).toHaveCount(0)
  })

  test('un administrador modifica y anula; el historial queda en los dos (US4)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'admin.demo')
    await page.goto('/presupuestos')
    const original = await emitirPresupuestoPorLaApi(page)

    // Modificar una línea: se emite el siguiente PRE y el original queda sustituido.
    await page.goto(`/presupuestos/${original.id}`)
    let consulta = page.getByRole('dialog', { name: `Presupuesto ${original.num_serie}` })
    await consulta.getByRole('link', { name: 'Modificar' }).click()
    const modal = page.getByRole('dialog', { name: `Modificar presupuesto ${original.num_serie}` })
    const precio = modal.getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' })
    await precio.fill('650')
    const respuesta = page.waitForResponse((r) => r.url().endsWith('/modificacion'))
    await modal.getByRole('button', { name: 'Guardar' }).click()
    const motivo = page.getByRole('alertdialog', { name: `¿Sustituir ${original.num_serie}?` })
    await motivo.getByRole('textbox', { name: /Motivo/ }).fill('Nuevo precio del oro')
    await motivo.getByRole('button', { name: 'Emitir el nuevo' }).click()
    const nuevo = (await (await respuesta).json()) as PresupuestoCreado
    expect(nuevo.num_serie).not.toBe(original.num_serie)
    await expect(
      page.getByText(`Se ha emitido ${nuevo.num_serie}. ${original.num_serie} queda sustituido`),
    ).toBeVisible()
    consulta = page.getByRole('dialog', { name: `Presupuesto ${nuevo.num_serie}` })
    await expect(consulta.getByText(/Sustituye a/)).toBeVisible()

    // El original: sustituido, con el motivo y el enlace al nuevo.
    await consulta.getByRole('link', { name: original.num_serie }).click()
    consulta = page.getByRole('dialog', { name: `Presupuesto ${original.num_serie}` })
    await expect(consulta.getByText('Nuevo precio del oro')).toBeVisible()
    await expect(consulta.getByRole('link', { name: nuevo.num_serie }).first()).toBeVisible()
    await expect(consulta.getByRole('link', { name: 'Modificar' })).toHaveCount(0)

    // Anular el nuevo con un motivo: queda marcado y su PDF lo dice.
    await page.goto(`/presupuestos/${nuevo.id}`)
    consulta = page.getByRole('dialog', { name: `Presupuesto ${nuevo.num_serie}` })
    await consulta.getByRole('button', { name: 'Anular' }).click()
    const anular = page.getByRole('alertdialog', {
      name: `¿Anular el presupuesto ${nuevo.num_serie}?`,
    })
    await anular.getByRole('textbox', { name: /Motivo/ }).fill('Rechazado por el cliente')
    await anular.getByRole('button', { name: 'Anular presupuesto' }).click()
    await expect(page.getByText(`Presupuesto ${nuevo.num_serie} anulado`)).toBeVisible()
    await expect(consulta.getByText('Rechazado por el cliente')).toBeVisible()
    await expect(consulta.getByText('Anulado').first()).toBeVisible()
    await expect(consulta.getByRole('button', { name: 'Convertir en factura' })).toHaveCount(0)
    const pdf = await page.request.get(`/api/v1/presupuestos/${nuevo.id}/pdf`)
    expect(pdf.status()).toBe(200)
  })

  test('un empleado no ve «Modificar» ni «Anular» (US4)', async ({ page }) => {
    await iniciarSesion(page, 'empleado.demo')
    await page.goto('/presupuestos')
    const presupuesto = await emitirPresupuestoPorLaApi(page)

    await page.goto(`/presupuestos/${presupuesto.id}`)
    const consulta = page.getByRole('dialog', { name: `Presupuesto ${presupuesto.num_serie}` })
    await expect(consulta.getByRole('button', { name: 'Convertir en factura' })).toBeVisible()
    await expect(consulta.getByRole('button', { name: 'Anular' })).toHaveCount(0)
    await expect(consulta.getByRole('link', { name: 'Modificar' })).toHaveCount(0)
  })
})
