import { expect, test } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'
import { compose, CONTRASENA, envejecerSesiones } from './helpers/entorno'

test.describe('Acceso seguro (US1)', () => {
  test('sin sesión redirige al acceso y, tras identificarse, vuelve a la ruta', async ({
    page,
  }) => {
    await page.goto('/clientes?estado=todos')
    await expect(page).toHaveURL(/\/acceso\?volver=/)

    await page.getByLabel('Usuario').fill('admin.demo')
    await page.getByLabel('Contraseña').fill(CONTRASENA)
    await page.getByRole('button', { name: 'Entrar' }).click()

    await expect(page).toHaveURL(/\/clientes\?.*estado=todos/)
    await expect(page.getByRole('heading', { name: 'Clientes' })).toBeVisible()
    const menu = page.getByRole('navigation', { name: 'Navegación principal' })
    await expect(menu.getByText('Próximamente')).toHaveCount(1) // Presupuestos (Facturas, desde 002)
    await expect(menu.getByRole('link', { name: 'Facturas' })).toBeVisible()
    await expect(menu.getByRole('link', { name: 'Configuración' })).toBeVisible()
  })

  test('mensajes genéricos idénticos para usuario inexistente y contraseña errónea', async ({
    page,
  }) => {
    await page.goto('/acceso')
    const intentos: [string, string][] = [
      ['no.existe', 'lo-que-sea-largo'],
      ['admin.demo', 'contraseña-incorrecta'],
    ]
    for (const [usuario, contrasena] of intentos) {
      await page.getByLabel('Usuario').fill(usuario)
      await page.getByLabel('Contraseña').fill(contrasena)
      await page.getByRole('button', { name: 'Entrar' }).click()
      await expect(page.getByRole('alert')).toHaveText('Usuario o contraseña incorrectos.')
    }
  })

  test('tras cinco fallos la cuenta queda bloqueada aunque la contraseña sea correcta', async ({
    page,
  }) => {
    await page.goto('/acceso')
    await page.getByLabel('Usuario').fill('vendedor.demo')
    for (let i = 0; i < 5; i++) {
      await page.getByLabel('Contraseña').fill(`intento-fallido-${i}-xx`)
      await page.getByRole('button', { name: 'Entrar' }).click()
      await expect(page.getByRole('alert')).toBeVisible()
    }
    await page.getByLabel('Contraseña').fill(CONTRASENA)
    await page.getByRole('button', { name: 'Entrar' }).click()

    await expect(page.getByRole('alert')).toHaveText('Usuario o contraseña incorrectos.')
    await expect(page).toHaveURL(/\/acceso/)
  })

  test('cerrar sesión invalida el acceso', async ({ page }) => {
    await iniciarSesion(page, 'empleado.demo')

    await page.getByRole('button', { name: /Menú de/ }).click()
    await page.getByRole('menuitem', { name: 'Cerrar sesión' }).click()

    await expect(page).toHaveURL(/\/acceso/)
    await page.goto('/clientes')
    await expect(page).toHaveURL(/\/acceso/)
  })

  test('la sesión caducada lleva al acceso y vuelve a la pantalla tras identificarse', async ({
    page,
  }) => {
    await iniciarSesion(page, 'empleado.demo')
    envejecerSesiones('empleado.demo')

    await page.getByPlaceholder('Buscar nombre, NIF o localidad').fill('ana')

    await expect(page).toHaveURL(/\/acceso\?volver=/)
    await expect(page.getByText('Tu sesión ha caducado. Vuelve a identificarte.')).toBeVisible()
    await page.getByLabel('Usuario').fill('empleado.demo')
    await page.getByLabel('Contraseña').fill(CONTRASENA)
    await page.getByRole('button', { name: 'Entrar' }).click()
    await expect(page).toHaveURL(/\/clientes/)
  })

  test('contraseña temporal: obliga a cambiarla antes de continuar', async ({ page }) => {
    const salida = compose('exec -T api-e2e joyeria restablecer-admin --usuario admin.demo')
    const temporal = /Contraseña temporal: (\S+)/.exec(salida)?.[1]
    expect(temporal).toBeTruthy()

    await page.goto('/acceso')
    await page.getByLabel('Usuario').fill('admin.demo')
    await page.getByLabel('Contraseña').fill(temporal ?? '')
    await page.getByRole('button', { name: 'Entrar' }).click()
    await expect(page).toHaveURL(/\/cambiar-contrasena/)
    await page.goto('/clientes')
    await expect(page).toHaveURL(/\/cambiar-contrasena/)

    await page.getByLabel('Contraseña actual').fill(temporal ?? '')
    await page.getByLabel('Contraseña nueva', { exact: true }).fill(CONTRASENA)
    await page.getByLabel('Repite la contraseña nueva').fill(CONTRASENA)
    await page.getByRole('button', { name: 'Cambiar contraseña' }).click()

    await expect(page).toHaveURL(/\/clientes/)
  })

  test('pantallas de página no encontrada y de acceso denegado', async ({ page }) => {
    await iniciarSesion(page, 'empleado.demo')

    await page.goto('/no-existe')
    await expect(page.getByRole('heading', { name: 'Página no encontrada' })).toBeVisible()

    await page.goto('/configuracion')
    await expect(page.getByRole('heading', { name: 'Acceso denegado' })).toBeVisible()
    await expect(
      page.getByRole('navigation', { name: 'Navegación principal' }).getByRole('link', {
        name: 'Configuración',
      }),
    ).toHaveCount(0)
  })
})
