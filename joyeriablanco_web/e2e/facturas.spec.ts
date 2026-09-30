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

/** Emite por la API, con la sesión del navegador, una factura a un cliente nuevo: por defecto,
 * de dos líneas con IVA. */
async function emitirPorLaApi(
  page: Page,
  lineas: { unidades: string; descripcion: string; precio_unitario: string }[] = [
    { unidades: '1', descripcion: 'Anillo', precio_unitario: '1200.00' },
    { unidades: '2', descripcion: 'Ajuste', precio_unitario: '45.00' },
  ],
): Promise<FacturaCreada & { cliente: string }> {
  const sesion = (await (await page.request.get('/api/v1/sesion')).json()) as {
    csrf_token: string
  }
  // Como el navegador: CSRF y origen de la página (la API rechaza otros orígenes).
  const cabeceras = {
    'X-CSRF-Token': sesion.csrf_token,
    Origin: new URL(page.url()).origin,
  }
  const numero = unico()
  const nombre = `Cliente Corrección ${String(numero)}`
  const cliente = await page.request.post('/api/v1/clientes', {
    headers: cabeceras,
    data: {
      tipo: 'particular',
      nombre,
      identificacion_tipo: 'NIF',
      identificacion_numero: dni(numero),
      direccion: 'Calle Recogidas, 12',
      codigo_postal: '18005',
      localidad: 'Granada',
    },
  })
  expect(cliente.status()).toBe(201)
  const { id } = (await cliente.json()) as { id: string }
  const factura = await page.request.post('/api/v1/facturas', {
    headers: { ...cabeceras, 'Idempotency-Key': crypto.randomUUID() },
    data: {
      fecha_expedicion: new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid' }).format(
        new Date(),
      ),
      cliente_id: id,
      lineas,
    },
  })
  expect(factura.status()).toBe(201)
  return { ...((await factura.json()) as FacturaCreada), cliente: nombre }
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

  test('correcciones del administrador: reemisión, rectificativa R4, anular la rectificativa y anular (US5)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'admin.demo')
    const original = await emitirPorLaApi(page)

    // 1. Reemisión: «no debió emitirse» anula la original y emite la siguiente FAC.
    await page.goto(`/facturas/${original.id}`)
    let modal = page.getByRole('dialog', { name: `Factura ${original.num_serie}` })
    await modal.getByRole('link', { name: 'Modificar' }).click()
    const modificar = page.getByRole('dialog', { name: `Modificar factura ${original.num_serie}` })
    await modificar.getByRole('button', { name: 'Guardar' }).click()
    let motivo = page.getByRole('alertdialog', { name: 'Motivo de la modificación' })
    await motivo.locator('label', { hasText: /no debió emitirse/ }).click()
    await motivo.getByRole('textbox', { name: /Explica el motivo/ }).fill('Número equivocado')
    await motivo.getByRole('button', { name: 'Confirmar' }).click()
    await expect(page.getByText(new RegExp(`${original.num_serie} queda anulada`))).toBeVisible()
    modal = page.getByRole('dialog', { name: /^Factura FAC-/ })
    await expect(modal.getByText(`Sustituye a ${original.num_serie}, anulada`)).toBeVisible()
    const reemitida = ((await modal.getByRole('heading').first().textContent()) ?? '').replace(
      'Factura ',
      '',
    )

    // 2. Rectificativa R4 de la reemitida, con otro precio.
    await modal.getByRole('link', { name: 'Modificar' }).click()
    const segunda = page.getByRole('dialog', { name: `Modificar factura ${reemitida}` })
    await segunda
      .getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' })
      .fill('1.100')
    await segunda.getByRole('button', { name: 'Guardar' }).click()
    motivo = page.getByRole('alertdialog', { name: 'Motivo de la modificación' })
    await motivo.locator('label', { hasText: /ya entregada/ }).click()
    await motivo.locator('label', { hasText: /Error en datos/ }).click()
    await motivo.getByRole('textbox', { name: /Explica el motivo/ }).fill('Precio mal')
    await motivo.getByRole('button', { name: 'Confirmar' }).click()
    await expect(page.getByText(new RegExp(`${reemitida} queda rectificada`))).toBeVisible()
    const rec = page.getByRole('dialog', { name: /^Factura REC-/ })
    await expect(rec.getByText('Rectificativa R4')).toBeVisible()
    await expect(rec.getByText(/Rectifica a/)).toBeVisible()

    // 3. Anular la rectificativa: la reemitida vuelve a estar vigente (FR-048).
    await rec.getByRole('button', { name: 'Anular' }).click()
    let anular = page.getByRole('alertdialog', { name: /^¿Anular la factura REC-/ })
    await expect(anular.getByText(`${reemitida} volverá a estar vigente.`)).toBeVisible()
    await anular.locator('label', { hasText: 'Declaro que esta factura no debió emitirse' }).click()
    await anular.getByRole('textbox', { name: /Motivo/ }).fill('Rectificación errónea')
    await anular.getByRole('button', { name: 'Anular factura' }).click()
    await expect(page.getByText(`${reemitida} vuelve a estar vigente`)).toBeVisible()
    await expect(rec.getByText('Anulada', { exact: true })).toBeVisible()
    await rec.getByRole('link', { name: reemitida }).first().click()
    modal = page.getByRole('dialog', { name: `Factura ${reemitida}` })
    await expect(modal.getByText('Rectificada', { exact: true })).toHaveCount(0)
    await expect(modal.getByText('Sin efecto')).toBeVisible()

    // 4. Anular la reemitida, ya vigente otra vez.
    await modal.getByRole('button', { name: 'Anular' }).click()
    anular = page.getByRole('alertdialog', { name: `¿Anular la factura ${reemitida}?` })
    await anular.locator('label', { hasText: 'Declaro que esta factura no debió emitirse' }).click()
    await anular.getByRole('textbox', { name: /Motivo/ }).fill('Venta cancelada')
    await anular.getByRole('button', { name: 'Anular factura' }).click()
    await expect(page.getByText(`Factura ${reemitida} anulada`)).toBeVisible()
    await expect(modal.getByText('Anulada', { exact: true })).toBeVisible()
    await expect(modal.getByRole('button', { name: 'Anular' })).toHaveCount(0)
  })

  test('oro de inversión sin IVA: previsualizar, emitir, consultar con la mención y el IBAN, y verla «Exenta» (FR-052, FR-053)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'empleado.demo')
    await page.goto('/facturas/nueva')
    const nueva = page.getByRole('dialog', { name: 'Nueva factura' })
    await expect(nueva.getByText('Se asigna al emitir')).toBeVisible()
    const { nombre } = await nuevoClienteDesdeElModal(page, nueva, 'Cliente Lingote')
    await nueva
      .getByRole('textbox', { name: 'Descripción de la línea 1' })
      .fill('Lingote de oro 100 g')
    await nueva
      .getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' })
      .fill('7.450')
    await nueva.locator('label', { hasText: 'Sin IVA (oro de inversión)' }).click()
    const mencion = 'Operación exenta de IVA (art. 140 bis.Uno.1.º de la Ley 37/1992)'
    await expect(nueva.getByText('Base exenta')).toBeVisible()
    await expect(nueva.getByText('IVA', { exact: true })).toBeVisible()
    await expect(nueva.getByText('IVA (21 %)')).toHaveCount(0)
    await expect(nueva.getByText(mencion)).toBeVisible()

    const respuesta = page.waitForResponse(
      (r) => r.url().endsWith('/api/v1/facturas') && r.request().method() === 'POST',
    )
    await nueva.getByRole('button', { name: 'Emitir factura' }).click()
    await page
      .getByRole('alertdialog', { name: '¿Emitir la factura?' })
      .getByRole('button', { name: 'Emitir factura' })
      .click()
    const creada = (await (await respuesta).json()) as FacturaCreada & {
      oro_inversion: boolean
      totales: { importe_total: string }
    }
    expect(creada.oro_inversion).toBe(true)
    expect(creada.totales.importe_total).toBe('7450.00')

    // Consulta: la mención del ROF art. 6.1.j y el IBAN del emisor (datos demo).
    await page.goto(`/facturas/${creada.id}`)
    const detalle = page.getByRole('dialog', { name: `Factura ${creada.num_serie}` })
    await expect(detalle.getByText(mencion)).toBeVisible()
    await expect(detalle.getByRole('group', { name: 'Pago' })).toContainText(
      'ES91 2100 0418 4502 0005 1332',
    )
    await detalle.getByRole('button', { name: 'Cerrar', exact: true }).click()

    // Listado: «Exenta» en la columna del IVA (visible desde 1440 px).
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.getByPlaceholder('Buscar número, cliente o NIF').fill(nombre)
    const tabla = page.getByRole('table', { name: 'Listado de facturas' })
    await expect(tabla.getByRole('row')).toHaveCount(2)
    await expect(tabla.getByRole('cell', { name: 'Exenta' })).toBeVisible()
  })

  test('rectificar a exenta un lingote facturado con IVA por error (US5-9)', async ({ page }) => {
    await iniciarSesion(page, 'admin.demo')
    const original = await emitirPorLaApi(page, [
      { unidades: '1', descripcion: 'Lingote de oro 100 g', precio_unitario: '7450.00' },
    ])

    await page.goto(`/facturas/${original.id}/modificar`)
    const modificar = page.getByRole('dialog', { name: `Modificar factura ${original.num_serie}` })
    const casilla = modificar.getByRole('checkbox', { name: 'Sin IVA (oro de inversión)' })
    await expect(casilla).not.toBeChecked()
    await modificar.locator('label', { hasText: 'Sin IVA (oro de inversión)' }).click()
    await expect(casilla).toBeChecked()
    await modificar.getByRole('button', { name: 'Guardar' }).click()
    const motivo = page.getByRole('alertdialog', { name: 'Motivo de la modificación' })
    await motivo.locator('label', { hasText: /ya entregada/ }).click()
    await motivo.locator('label', { hasText: /IVA mal aplicado/ }).click()
    await motivo.getByRole('textbox', { name: /Explica el motivo/ }).fill('Oro de inversión')
    await motivo.getByRole('button', { name: 'Confirmar' }).click()

    await expect(
      page.getByText(new RegExp(`${original.num_serie} queda rectificada`)),
    ).toBeVisible()
    const rec = page.getByRole('dialog', { name: /^Factura REC-/ })
    await expect(rec.getByText('Rectificativa R1')).toBeVisible()
    await expect(rec.getByText('Base exenta')).toBeVisible()
    await expect(
      rec.getByText('Operación exenta de IVA (art. 140 bis.Uno.1.º de la Ley 37/1992)'),
    ).toBeVisible()
  })

  test('un empleado consulta una factura sin acciones de corrección (US5, FR-023)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'empleado.demo')
    const factura = await emitirPorLaApi(page)

    await page.goto(`/facturas/${factura.id}`)
    const modal = page.getByRole('dialog', { name: `Factura ${factura.num_serie}` })
    await expect(modal.getByRole('button', { name: 'Cerrar', exact: true })).toBeVisible()
    await expect(modal.getByRole('button', { name: 'Anular' })).toHaveCount(0)
    await expect(modal.getByRole('link', { name: 'Modificar' })).toHaveCount(0)
    await page.goto(`/facturas/${factura.id}/modificar`)
    await expect(page).toHaveURL(/\/acceso-denegado/)
  })

  test('fecha libre: una factura anterior a la última de la serie y una rectificativa de otro día (FR-018)', async ({
    page,
  }) => {
    const dia = (desfase: number) =>
      new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid' }).format(
        new Date(Date.now() - desfase * 86_400_000),
      )
    await iniciarSesion(page, 'admin.demo')
    await emitirPorLaApi(page) // la última de la serie lleva la fecha de hoy

    await page.goto('/facturas/nueva')
    const nueva = page.getByRole('dialog', { name: 'Nueva factura' })
    await expect(nueva.getByText('Se asigna al emitir')).toBeVisible()
    await nueva.getByLabel(/^Fecha/).fill(dia(3))
    await nuevoClienteDesdeElModal(page, nueva, 'Cliente Fecha')
    await nueva.getByRole('textbox', { name: 'Descripción de la línea 1' }).fill('Anillo')
    await nueva.getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' }).fill('500')
    const emision = page.waitForResponse(
      (r) => r.url().endsWith('/api/v1/facturas') && r.request().method() === 'POST',
    )
    await nueva.getByRole('button', { name: 'Emitir factura' }).click()
    await page
      .getByRole('alertdialog', { name: '¿Emitir la factura?' })
      .getByRole('button', { name: 'Emitir factura' })
      .click()
    const factura = (await (await emision).json()) as FacturaCreada & { fecha_expedicion: string }
    expect(factura.fecha_expedicion).toBe(dia(3))

    // Rectificativa con fecha de hace dos días: posterior a la operación, anterior a hoy.
    await page.goto(`/facturas/${factura.id}/modificar`)
    const modificar = page.getByRole('dialog', { name: `Modificar factura ${factura.num_serie}` })
    const fecha = modificar.getByLabel(/^Fecha/)
    await expect(fecha).toHaveAttribute('min', dia(3))
    await fecha.fill(dia(2))
    await modificar
      .getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' })
      .fill('450')
    await modificar.getByRole('button', { name: 'Guardar' }).click()
    const motivo = page.getByRole('alertdialog', { name: 'Motivo de la modificación' })
    await motivo.locator('label', { hasText: /ya entregada/ }).click()
    await motivo.locator('label', { hasText: /Devolución, descuento/ }).click()
    await motivo.getByRole('textbox', { name: /Explica el motivo/ }).fill('Descuento')
    await motivo.getByRole('button', { name: 'Confirmar' }).click()
    const rec = page.getByRole('dialog', { name: /^Factura REC-/ })
    await expect(rec.getByText('Rectificativa R1')).toBeVisible()
    const enPantalla = dia(2).split('-').reverse().join('/') // AAAA-MM-DD → DD/MM/AAAA
    await expect(rec.getByText(enPantalla).first()).toBeVisible()
  })
})
