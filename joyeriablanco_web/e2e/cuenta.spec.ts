import { expect, test } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'
import { CONTRASENA } from './helpers/entorno'

const NUEVA = 'E2e-Granate-Onix-Perla-2026'

test('Mi cuenta: el cambio de contraseña cierra las demás sesiones (US6)', async ({
  page,
  browser,
}) => {
  const otroEquipo = await browser.newPage()
  await iniciarSesion(otroEquipo, 'empleado.demo')
  await iniciarSesion(page, 'empleado.demo')

  await page.getByRole('button', { name: /Menú de/ }).click()
  await page.getByRole('menuitem', { name: 'Mi cuenta' }).click()
  await expect(page.getByRole('heading', { name: 'Mi cuenta' })).toBeVisible()

  // La política se explica al rechazar.
  await page.getByLabel('Contraseña actual').fill(CONTRASENA)
  await page.getByLabel('Contraseña nueva', { exact: true }).fill('empleado.demo-clave-2026')
  await page.getByLabel('Repite la contraseña nueva').fill('empleado.demo-clave-2026')
  await page.getByRole('button', { name: 'Cambiar contraseña' }).click()
  await expect(page.getByText('No puede contener tu nombre de usuario.')).toBeVisible()

  await page.getByLabel('Contraseña nueva', { exact: true }).fill(NUEVA)
  await page.getByLabel('Repite la contraseña nueva').fill(NUEVA)
  await page.getByRole('button', { name: 'Cambiar contraseña' }).click()
  await expect(
    page.getByText('Contraseña actualizada. Se han cerrado tus otras sesiones.'),
  ).toBeVisible()

  // El otro equipo pierde la sesión; este la conserva.
  await otroEquipo.getByPlaceholder('Buscar nombre, NIF o localidad').fill('joy')
  await expect(otroEquipo).toHaveURL(/\/acceso/)
  await page.goto('/clientes')
  await expect(page.getByRole('heading', { name: 'Clientes' })).toBeVisible()

  // La contraseña antigua ya no vale.
  await otroEquipo.getByLabel('Usuario').fill('empleado.demo')
  await otroEquipo.getByLabel('Contraseña').fill(CONTRASENA)
  await otroEquipo.getByRole('button', { name: 'Entrar' }).click()
  await expect(otroEquipo.getByRole('alert')).toHaveText('Usuario o contraseña incorrectos.')
  await otroEquipo.close()

  // Se restaura la contraseña conocida para el resto de recorridos.
  await page.goto('/cuenta')
  await page.getByLabel('Contraseña actual').fill(NUEVA)
  await page.getByLabel('Contraseña nueva', { exact: true }).fill(CONTRASENA)
  await page.getByLabel('Repite la contraseña nueva').fill(CONTRASENA)
  await page.getByRole('button', { name: 'Cambiar contraseña' }).click()
  await expect(page.getByText('Contraseña actualizada.', { exact: false })).toBeVisible()
})
