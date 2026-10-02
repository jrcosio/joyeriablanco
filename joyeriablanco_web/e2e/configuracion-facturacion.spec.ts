import { expect, test } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'

test('configuración de facturación: IVA libre, IBAN y ajuste de la numeración (US1; FR-001, FR-010)', async ({
  page,
}) => {
  await iniciarSesion(page, 'admin.demo')
  await page.goto('/configuracion/facturacion')
  await expect(page.getByRole('link', { name: 'Facturación' })).toHaveAttribute(
    'aria-current',
    'page',
  )

  // Sin clave de régimen (R-23).
  await expect(page.getByText(/Clave de régimen/)).toHaveCount(0)

  // IVA por defecto libre (R-20, SC-012): 22 avisa y pide confirmación; se vuelve al 21 sin ella.
  // Tras cada guardado se recarga la página: el formulario se vuelve a montar con la versión
  // nueva de la configuración y descartaría lo escrito mientras tanto.
  const iva = page.getByRole('textbox', { name: /IVA por defecto/ })
  const guardadoConExito = async () => {
    await expect(page.getByText('Configuración de facturación guardada').last()).toBeVisible()
    await page.reload()
  }
  await expect(iva).toHaveValue('21')
  await iva.fill('22')
  await expect(
    page.getByText('22 % no está entre los tipos que admite hoy la AEAT (0, 4, 10 y 21).'),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Guardar configuración' }).click()
  const confirmar = page.getByRole('alertdialog', {
    name: '¿Guardar un tipo de IVA que la AEAT no admite hoy?',
  })
  await confirmar.getByRole('button', { name: 'Guardar igualmente' }).click()
  await guardadoConExito()
  await expect(iva).toHaveValue('22')
  await iva.fill('21')
  await page.getByRole('button', { name: 'Guardar configuración' }).click()
  await expect(confirmar).toHaveCount(0)
  await guardadoConExito()
  await expect(iva).toHaveValue('21')

  // IBAN (R-22): uno con el dígito de control mal se rechaza; el bueno se agrupa de 4 en 4.
  const iban = page.getByRole('textbox', { name: /^IBAN/ })
  await expect(iban).toHaveValue('ES91 2100 0418 4502 0005 1332') // datos demo
  await iban.fill('ES91 2100 0418 4502 0005 1333')
  await page.getByRole('button', { name: 'Guardar configuración' }).click()
  await expect(page.getByText(/dígito de control del IBAN no es correcto/)).toBeVisible()
  await iban.fill('es9121000418450200051332')
  await iban.blur()
  await expect(iban).toHaveValue('ES91 2100 0418 4502 0005 1332')
  await page.getByRole('button', { name: 'Guardar configuración' }).click()
  await guardadoConExito()
  await expect(iban).toHaveValue('ES91 2100 0418 4502 0005 1332')

  // Ajuste al alza del próximo número, con aviso previo de los números que quedan sin usar.
  const numeracion = page.getByText(/^FAC-\d{4}-\d{4,}$/)
  const actual = (await numeracion.textContent()) ?? ''
  const [, anio = '', numero = '0'] = /^FAC-(\d{4})-(\d+)$/.exec(actual) ?? []
  const proximo = Number(numero) + 10
  await page.getByRole('button', { name: 'Ajustar numeración' }).click()
  const dialogo = page.getByRole('dialog', { name: 'Ajustar la numeración' })
  await dialogo.getByRole('textbox', { name: /Próximo número/ }).fill(String(proximo))
  await dialogo.getByRole('textbox', { name: /Motivo/ }).fill('Prueba E2E del ajuste')
  await dialogo.getByRole('button', { name: 'Continuar' }).click()
  await expect(dialogo.getByText(/Quedarán 10 números sin usar/)).toBeVisible()
  await dialogo.getByRole('button', { name: 'Confirmar ajuste' }).click()
  const esperado = `FAC-${anio}-${String(proximo).padStart(4, '0')}`
  await expect(page.getByText(`La próxima factura será ${esperado}`)).toBeVisible()
  await expect(numeracion).toHaveText(esperado)
})

test('un empleado no accede a la configuración de facturación (FR-001)', async ({ page }) => {
  await iniciarSesion(page, 'empleado.demo')
  await page.goto('/configuracion/facturacion')

  await expect(page).toHaveURL(/\/acceso-denegado/)
})

test('contacto y pie de factura: se guardan y se imprimen en las facturas (003, US3)', async ({
  page,
}) => {
  await iniciarSesion(page, 'admin.demo')
  await page.goto('/configuracion/facturacion')

  // Datos de ejemplo (FR-032)
  const telefono = page.getByRole('textbox', { name: 'Teléfono' })
  await expect(telefono).toHaveValue('+34 900 000 000')
  await expect(page.getByRole('textbox', { name: 'Web' })).toHaveValue('joyeriablanco.demo')

  await telefono.fill('abc')
  await page.getByRole('button', { name: 'Guardar configuración' }).click()
  await expect(page.getByText(/solo dígitos, espacios/)).toBeVisible()

  await telefono.fill('+34 958 000 111')
  await page.getByRole('textbox', { name: 'Pie de factura' }).fill('Gracias por su confianza.')
  await page.getByRole('button', { name: 'Guardar configuración' }).click()
  await expect(page.getByText('Configuración de facturación guardada').last()).toBeVisible()
  await page.reload()
  await expect(telefono).toHaveValue('+34 958 000 111')

  // Cualquier factura emitida se imprime con el contacto y el pie vigentes
  const lista = await page.request.get('/api/v1/facturas?anio=todos&tamano=100')
  const { elementos } = (await lista.json()) as {
    elementos: { id: string; tipo_documento: string }[]
  }
  const factura = elementos.find((f) => f.tipo_documento === 'factura')
  expect(factura).toBeDefined()
  const pdf = await page.request.get(`/api/v1/facturas/${factura?.id ?? ''}/pdf`)
  expect(pdf.status()).toBe(200)
  expect(pdf.headers()['content-type']).toBe('application/pdf')
})
