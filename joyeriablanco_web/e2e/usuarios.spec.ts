import { expect, test } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'
import { CONTRASENA, unico } from './helpers/entorno'

test('gestión de usuarios: alta, primer acceso, desactivación inmediata y auditoría (US5)', async ({
  page,
  browser,
}) => {
  const nombreUsuario = `e2e.${unico()}`
  await iniciarSesion(page, 'admin.demo')
  await page
    .getByRole('navigation', { name: 'Navegación principal' })
    .getByRole('link', { name: 'Configuración' })
    .click()
  await expect(page).toHaveURL(/\/configuracion\/usuarios/)

  // Alta con contraseña temporal mostrada una sola vez.
  await page.getByRole('button', { name: 'Nuevo usuario' }).click()
  const alta = page.getByRole('dialog', { name: 'Nuevo usuario' })
  await alta.getByRole('textbox', { name: 'Nombre', exact: true }).fill('Empleada E2E')
  await alta.getByRole('textbox', { name: 'Nombre de usuario' }).fill(nombreUsuario)
  await alta.getByRole('button', { name: 'Crear usuario' }).click()
  const dialogo = page.getByRole('alertdialog', { name: 'Contraseña temporal' })
  const temporal = (await dialogo.getByLabel('Contraseña temporal').textContent())?.trim() ?? ''
  expect(temporal).toMatch(/^[A-Za-z2-9]{4}(-[A-Za-z2-9]{4}){3}$/)
  await dialogo.getByRole('button', { name: 'He anotado la contraseña' }).click()
  await expect(page.getByRole('table', { name: 'Usuarios del sistema' })).toContainText(
    nombreUsuario,
  )

  // Primer acceso del empleado: cambio obligatorio y sin Configuración.
  const empleado = await browser.newPage()
  await empleado.goto('/acceso')
  await empleado.getByLabel('Usuario').fill(nombreUsuario)
  await empleado.getByLabel('Contraseña').fill(temporal)
  await empleado.getByRole('button', { name: 'Entrar' }).click()
  await expect(empleado).toHaveURL(/\/cambiar-contrasena/)
  await empleado.getByLabel('Contraseña actual').fill(temporal)
  await empleado.getByLabel('Contraseña nueva', { exact: true }).fill(CONTRASENA)
  await empleado.getByLabel('Repite la contraseña nueva').fill(CONTRASENA)
  await empleado.getByRole('button', { name: 'Cambiar contraseña' }).click()
  await expect(empleado).toHaveURL(/\/clientes/)
  await expect(
    empleado.getByRole('navigation', { name: 'Navegación principal' }).getByRole('link', {
      name: 'Configuración',
    }),
  ).toHaveCount(0)

  // El administrador lo desactiva mientras tiene la sesión abierta.
  await page.getByRole('button', { name: 'Acciones para Empleada E2E' }).click()
  await page.getByRole('menuitem', { name: 'Desactivar' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Desactivar' }).click()
  await expect(page.getByText('Empleada E2E desactivado.')).toBeVisible()

  // Su siguiente acción lo lleva al acceso.
  await empleado.getByPlaceholder('Buscar nombre, NIF o localidad').fill('joy')
  await expect(empleado).toHaveURL(/\/acceso/)
  await empleado.close()

  // La auditoría muestra la desactivación.
  await page.getByRole('link', { name: 'Auditoría' }).click()
  await page.getByRole('button', { name: /Tipo de evento/ }).click()
  await page.getByRole('option', { name: 'Usuario desactivado' }).click()
  const eventos = page.getByRole('table', { name: 'Eventos de auditoría' })
  await expect(eventos.getByText('Usuario desactivado').first()).toBeVisible()
})
