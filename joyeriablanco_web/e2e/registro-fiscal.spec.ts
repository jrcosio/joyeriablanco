import { expect, test } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'

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
})
