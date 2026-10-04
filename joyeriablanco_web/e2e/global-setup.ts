/**
 * Prepara la API de E2E: la levanta, reconstruye su BD y carga datos de ejemplo con una
 * contraseña conocida (research R-16).
 *
 * Desde 004 (research R-6) genera antes un certificado de firma de pruebas, y al final reinicia la
 * API para que su evento de inicio quede firmado en la BD ya reconstruida.
 */
import { API_E2E, compose, CONTRASENA } from './helpers/entorno'

// Las mismas ruta y contraseña que `api-e2e` en docker-compose.yml.
const CERTIFICADO = '/app/var/certificados/pruebas-e2e.p12'

async function esperarApi(): Promise<void> {
  for (let intento = 0; intento < 60; intento++) {
    try {
      const respuesta = await fetch(`${API_E2E}/api/salud`)
      if (respuesta.ok) return
    } catch {
      // aún arrancando
    }
    await new Promise((resolver) => setTimeout(resolver, 1000))
  }
  throw new Error('La API de E2E no responde en http://localhost:8001')
}

export default async function globalSetup(): Promise<void> {
  compose('up -d --build api-e2e')
  await esperarApi()
  compose(
    `exec -T api-e2e joyeria generar-certificado-pruebas --destino ${CERTIFICADO} --contrasena pruebas`,
  )
  compose('exec -T api-e2e joyeria reiniciar-bd-e2e')
  compose(
    `exec -T api-e2e joyeria cargar-datos-ejemplo --clientes 40 --contrasena-demo ${CONTRASENA}`,
  )
  compose('restart api-e2e')
  await esperarApi()
}
