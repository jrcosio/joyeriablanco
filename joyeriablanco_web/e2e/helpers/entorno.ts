/** Utilidades de entorno E2E: docker compose, SQL directo y datos conocidos. */
import { execSync } from 'node:child_process'
import path from 'node:path'

export const RAIZ = path.resolve(import.meta.dirname, '../../..')
export const CONTRASENA = 'E2e-Zafiro-Topacio-2026'
export const API_E2E = 'http://localhost:8001'

export function compose(args: string, opciones: { input?: string } = {}): string {
  return execSync(`docker compose --profile e2e ${args}`, {
    cwd: RAIZ,
    encoding: 'utf8',
    stdio: ['pipe', 'pipe', 'inherit'],
    ...(opciones.input !== undefined ? { input: opciones.input } : {}),
  })
}

/** Ejecuta SQL como superusuario en la BD de E2E (solo para preparar escenarios de prueba). */
export function sql(consulta: string): string {
  return compose(
    `exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -At -U "$POSTGRES_USER" -d joyeriablanco_e2e'`,
    { input: consulta },
  )
}

/** Simula 31 minutos de inactividad en todas las sesiones del usuario (FR-003). */
export function envejecerSesiones(nombreUsuario: string): void {
  sql(
    `UPDATE sesiones SET ultima_actividad_en = now() - interval '31 minutes' ` +
      `WHERE usuario_id IN (SELECT id FROM usuarios WHERE nombre_usuario = '${nombreUsuario}');`,
  )
}

const LETRAS = 'TRWAGMYFPDXBNJZSQVHLCKE'

/** DNI válido (algoritmo oficial de la letra, research R-20.2) a partir de un número. */
export function dni(numero: number): string {
  return `${String(numero).padStart(8, '0')}${LETRAS[numero % 23] ?? ''}`
}

/** Número pseudoaleatorio para identificaciones únicas en cada ejecución. */
export function unico(): number {
  return 10_000_000 + Math.floor(Math.random() * 89_999_999)
}
