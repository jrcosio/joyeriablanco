import { expect, test } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'
import { CONTRASENA, dni, unico } from './helpers/entorno'

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

test('eliminación de un usuario desactivado: conserva lo que registró y libera su nombre (FR-061)', async ({
  page,
  browser,
}) => {
  const n = unico()
  const nombre = `Eliminable E2E ${n}`
  const nombreUsuario = `e2e.del.${n}`
  const cliente = `Cliente de ${nombre}`
  await iniciarSesion(page, 'admin.demo')
  await page
    .getByRole('navigation', { name: 'Navegación principal' })
    .getByRole('link', { name: 'Configuración' })
    .click()

  const crearUsuario = async (nombreVisible: string) => {
    await page.getByRole('button', { name: 'Nuevo usuario' }).click()
    const alta = page.getByRole('dialog', { name: 'Nuevo usuario' })
    await alta.getByRole('textbox', { name: 'Nombre', exact: true }).fill(nombreVisible)
    await alta.getByRole('textbox', { name: 'Nombre de usuario' }).fill(nombreUsuario)
    await alta.getByRole('button', { name: 'Crear usuario' }).click()
    const dialogo = page.getByRole('alertdialog', { name: 'Contraseña temporal' })
    const temporal = (await dialogo.getByLabel('Contraseña temporal').textContent())?.trim() ?? ''
    await dialogo.getByRole('button', { name: 'He anotado la contraseña' }).click()
    return temporal
  }

  // El empleado entra y da de alta un cliente.
  const temporal = await crearUsuario(nombre)
  const empleado = await browser.newPage()
  await empleado.goto('/acceso')
  await empleado.getByLabel('Usuario').fill(nombreUsuario)
  await empleado.getByLabel('Contraseña').fill(temporal)
  await empleado.getByRole('button', { name: 'Entrar' }).click()
  await empleado.getByLabel('Contraseña actual').fill(temporal)
  await empleado.getByLabel('Contraseña nueva', { exact: true }).fill(CONTRASENA)
  await empleado.getByLabel('Repite la contraseña nueva').fill(CONTRASENA)
  await empleado.getByRole('button', { name: 'Cambiar contraseña' }).click()
  await expect(empleado).toHaveURL(/\/clientes/)
  await empleado.getByRole('link', { name: 'Nuevo cliente' }).first().click()
  await empleado.getByLabel(/Nombre o razón social/).fill(cliente)
  await empleado.getByLabel(/Número de identificación/).fill(dni(n))
  await empleado.getByRole('button', { name: 'Crear cliente' }).click()
  await expect(empleado.getByText(`Cliente «${cliente}» creado.`)).toBeVisible()
  await empleado.close()

  // Sin desactivar no se ofrece eliminar; tras desactivarlo, sí.
  await page.getByRole('button', { name: `Acciones para ${nombre}` }).click()
  await expect(page.getByRole('menuitem', { name: 'Eliminar' })).toHaveCount(0)
  await page.getByRole('menuitem', { name: 'Desactivar' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Desactivar' }).click()
  await expect(page.getByText(`${nombre} desactivado.`)).toBeVisible()
  await page.getByRole('button', { name: `Acciones para ${nombre}` }).click()
  await page.getByRole('menuitem', { name: 'Eliminar' }).click()
  const confirmacion = page.getByRole('alertdialog', { name: 'Eliminar usuario' })
  await confirmacion.getByLabel(/Escribe el nombre de usuario/).fill(nombreUsuario)
  await confirmacion.getByRole('button', { name: 'Eliminar' }).click()
  await expect(page.getByText(`${nombre} eliminado.`)).toBeVisible()
  await expect(page.getByRole('table', { name: 'Usuarios del sistema' })).not.toContainText(
    nombreUsuario,
  )

  // Su nombre de usuario queda libre.
  await crearUsuario('Sucesora E2E')
  await expect(page.getByRole('table', { name: 'Usuarios del sistema' })).toContainText(
    'Sucesora E2E',
  )

  // La auditoría registra la eliminación y lo marca como eliminado.
  await page.getByRole('link', { name: 'Auditoría' }).click()
  await page.getByRole('button', { name: /Tipo de evento/ }).click()
  await page.getByRole('option', { name: 'Usuario eliminado' }).click()
  await expect(page).toHaveURL(/tipo=usuario_eliminado/)
  await expect(
    page
      .getByRole('table', { name: 'Eventos de auditoría' })
      .getByRole('row')
      .filter({ hasText: 'Usuario eliminado' })
      .filter({ hasText: `${nombre} (eliminado)` }),
  ).toHaveCount(1)

  // El cliente que registró se conserva y muestra quién lo creó.
  await page
    .getByRole('navigation', { name: 'Navegación principal' })
    .getByRole('link', { name: 'Clientes' })
    .click()
  await page.getByPlaceholder('Buscar nombre, NIF o localidad').fill(cliente)
  await page
    .getByRole('table', { name: 'Listado de clientes' })
    .getByRole('link', { name: `Editar cliente ${cliente}` })
    .click()
  await expect(page.getByRole('dialog').getByText(`${nombre} (eliminado)`)).toHaveCount(2)
})
