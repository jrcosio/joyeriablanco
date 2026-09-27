/**
 * Cliente HTTP tipado (openapi-fetch) sobre los tipos generados del OpenAPI de FastAPI.
 *
 * - Misma procedencia: las cookies de sesión viajan solas (research R-5).
 * - Añade `X-CSRF-Token` a toda petición que modifica datos (research R-6).
 * - Traduce `application/problem+json` a `ApiError`.
 * - Notifica al módulo de autenticación los 401 de sesión y los 403 de CSRF (FR-004, FR-011).
 */
import createClient, { type Middleware } from 'openapi-fetch'
import type { paths } from './schema.gen'

export interface CampoError {
  campo: string
  mensaje: string
}

export interface Problema {
  type: string
  title: string
  status: number
  detail?: string
  errores?: CampoError[]
  [clave: string]: unknown
}

export class ApiError extends Error {
  readonly status: number
  readonly problema: Problema

  constructor(problema: Problema) {
    super(problema.detail ?? problema.title)
    this.name = 'ApiError'
    this.status = problema.status
    this.problema = problema
  }

  /** Tipo corto del catálogo (`validacion`, `duplicado`, `conflicto-version`…). */
  get tipo(): string {
    return this.problema.type.replace(/^\/problemas\//, '')
  }

  /** Errores de validación indexados por campo. */
  get porCampo(): Record<string, string> {
    return Object.fromEntries((this.problema.errores ?? []).map((e) => [e.campo, e.mensaje]))
  }
}

const METODOS_MUTANTES = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])
const RUTA_SESION = '/api/v1/sesion'

let csrfToken: string | null = null
let alPerderSesion: ((problema: Problema) => void) | null = null

export function setCsrfToken(token: string | null): void {
  csrfToken = token
}

export function setAlPerderSesion(manejador: ((problema: Problema) => void) | null): void {
  alPerderSesion = manejador
}

function problemaGenerico(response: Response): Problema {
  return {
    type: '/problemas/red',
    title: response.status >= 500 ? 'Error del servidor' : 'Error inesperado',
    status: response.status,
    detail:
      response.status >= 500
        ? 'El servidor no ha podido completar la operación. Inténtalo de nuevo.'
        : 'No se ha podido completar la operación.',
  }
}

function comoProblema(cuerpo: unknown, response: Response): Problema {
  if (typeof cuerpo === 'object' && cuerpo !== null) {
    const posible = cuerpo as Partial<Problema>
    if (typeof posible.type === 'string' && typeof posible.title === 'string') {
      return { ...posible, status: response.status } as Problema
    }
  }
  return problemaGenerico(response)
}

export async function leerProblema(response: Response): Promise<Problema> {
  try {
    return comoProblema(await response.clone().json(), response)
  } catch {
    return problemaGenerico(response) // cuerpo no JSON
  }
}

const middleware: Middleware = {
  onRequest({ request }) {
    if (METODOS_MUTANTES.has(request.method) && csrfToken) {
      request.headers.set('X-CSRF-Token', csrfToken)
    }
    return request
  },
  async onResponse({ request, response }) {
    if (response.status !== 401 && response.status !== 403) return response
    const ruta = new URL(request.url).pathname
    // El login fallido y la comprobación inicial de sesión no son "sesión perdida".
    if (ruta === RUTA_SESION && request.method !== 'DELETE') return response
    const problema = await leerProblema(response)
    const perdida =
      problema.type === '/problemas/no-autenticado' || problema.type === '/problemas/csrf'
    if (perdida && alPerderSesion) alPerderSesion(problema)
    return response
  },
}

export const api = createClient<paths>({
  baseUrl: window.location.origin,
  // Se resuelve en cada llamada (permite interceptarlo en pruebas y entornos instrumentados).
  fetch: (peticion: Request) => globalThis.fetch(peticion),
})
api.use(middleware)

/** Devuelve los datos o lanza `ApiError` con el problema del servidor. */
export async function unwrap<R extends { data?: unknown; error?: unknown; response: Response }>(
  peticion: Promise<R>,
): Promise<Exclude<R['data'], undefined>> {
  let resultado: R
  try {
    resultado = await peticion
  } catch {
    throw new ApiError({
      type: '/problemas/red',
      title: 'Sin conexión',
      status: 0,
      detail:
        'No se ha podido conectar con el servidor. Comprueba la conexión e inténtalo de nuevo.',
    })
  }
  if (!resultado.response.ok) {
    // openapi-fetch ya ha leído el cuerpo del error y lo deja en `error`.
    throw new ApiError(comoProblema(resultado.error, resultado.response))
  }
  return resultado.data as Exclude<R['data'], undefined>
}
