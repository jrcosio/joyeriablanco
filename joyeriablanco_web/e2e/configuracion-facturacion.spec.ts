import { expect, test } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'

test('configuración de facturación: IVA y ajuste de la numeración (US1; FR-001, FR-010)', async ({
  page,
}) => {
  await iniciarSesion(page, 'admin.demo')
  await page.goto('/configuracion/facturacion')
  await expect(page.getByRole('link', { name: 'Facturación' })).toHaveAttribute(
    'aria-current',
    'page',
  )

  // IVA por defecto: se cambia y se vuelve a dejar al 21 %.
  const iva = page.getByRole('button', { name: /IVA por defecto/ })
  await expect(iva).toContainText('21 %')
  for (const tipo of ['10 %', '21 %']) {
    await iva.click()
    await page.getByRole('option', { name: tipo, exact: true }).click()
    await page.getByRole('button', { name: 'Guardar configuración' }).click()
    await expect(page.getByText('Configuración de facturación guardada')).toBeVisible()
    await expect(iva).toContainText(tipo)
  }

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
