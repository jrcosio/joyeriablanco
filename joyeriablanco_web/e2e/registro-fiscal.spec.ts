import { expect, test } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'
import { emitirPorLaApi } from './helpers/facturas'

/**
 * «Registro fiscal» de la modalidad No VERI*FACTU (004). El arranque de `api-e2e`, que reinicia
 * `global-setup` tras reconstruir la BD, deja su evento de inicio firmado.
 */
test.describe('Registro fiscal', () => {
  test('el administrador ve el inicio del funcionamiento y su detalle (US2, FR-016)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'admin.demo')
    await page.getByRole('link', { name: 'Registro fiscal' }).click()

    await expect(page.getByRole('heading', { name: 'Registro fiscal' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Eventos' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    const tabla = page.getByRole('table', { name: 'Registro de eventos' })
    const inicio = tabla.getByRole('row').filter({ hasText: 'Inicio del funcionamiento' }).first()
    await expect(inicio).toBeVisible()

    await inicio
      .getByRole('button', { name: /Ver el evento nº \d+: Inicio del funcionamiento/ })
      .click()
    const detalle = page.getByRole('dialog', { name: /Evento nº \d+ · Inicio del funcionamiento/ })
    await expect(detalle.getByText('JOYERIA BLANCO (PRUEBAS)')).toBeVisible()
    await expect(detalle.getByText('Huella correcta')).toBeVisible()
    await expect(detalle.getByText('Firma correcta')).toBeVisible()
  })

  test('un empleado no tiene «Registro fiscal»', async ({ page }) => {
    await iniciarSesion(page, 'empleado.demo')
    await expect(page.getByRole('link', { name: 'Facturas' }).first()).toBeVisible()
    await expect(page.getByRole('link', { name: 'Registro fiscal' })).toHaveCount(0)
  })

  test('comprobar la integridad deja sus eventos y no enciende ninguna alarma (US3, FR-017)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'admin.demo')
    await page.goto('/registro-fiscal?pestana=comprobar')

    await page.getByRole('button', { name: 'Comprobar integridad' }).click()
    await expect(page.getByText('Íntegra')).toBeVisible({ timeout: 30_000 })
    await expect(
      page.getByText(/registros de facturación y \d+ de evento comprobados/),
    ).toBeVisible()
    await expect(page.getByRole('alert')).toHaveCount(0) // ni banda de alarma ni error

    await page.getByRole('tab', { name: 'Eventos' }).click()
    const tabla = page.getByRole('table', { name: 'Registro de eventos' })
    await expect(
      tabla.getByText('Comprobación de los registros de facturación').first(),
    ).toBeVisible()
    await expect(tabla.getByText('Comprobación de los registros de evento').first()).toBeVisible()
  })

  test('desde una factura se llega a su registro en la cadena (US3, art. 7.h)', async ({
    page,
  }) => {
    await iniciarSesion(page, 'admin.demo')
    const creada = await emitirPorLaApi(page)

    await page.goto(`/facturas/${creada.id}`)
    const detalle = page.getByRole('dialog', { name: `Factura ${creada.num_serie}` })
    await detalle.getByRole('link', { name: 'Ver en la cadena' }).click()

    await expect(page.getByRole('tab', { name: 'Cadena' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByRole('heading', { name: /Registro de alta nº \d+/ })).toBeVisible()
    await expect(page.getByRole('link', { name: creada.num_serie })).toBeVisible()
    await expect(page.getByText('Firma correcta')).toBeVisible()
    await expect(page.getByText('Siguiente: no hay.')).toBeVisible()
    await page.getByRole('button', { name: /Anterior \(nº \d+\)/ }).click()
    await expect(page.getByText('Siguiente: no hay.')).toHaveCount(0)
  })
})
