import { expect, type Page } from '@playwright/test'
import { CONTRASENA } from './entorno'

export async function iniciarSesion(page: Page, usuario: string, contrasena = CONTRASENA) {
  await page.goto('/acceso')
  await page.getByLabel('Usuario').fill(usuario)
  await page.getByLabel('Contraseña').fill(contrasena)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page).toHaveURL(/\/clientes/)
}
