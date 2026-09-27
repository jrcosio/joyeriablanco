import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryHistory, createRouter, RouterProvider } from '@tanstack/react-router'
import { render } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { SesionSalida } from '../api/tipos'
import { configurarPerdidaDeSesion } from '../auth/perdida'
import { routeTree } from '../routeTree.gen'
import { server } from './msw'

/** Renderiza la aplicación real (rutas y guardas) en una ruta dada, con la API simulada por MSW. */
export function renderApp(ruta: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [ruta] }),
  })
  configurarPerdidaDeSesion(queryClient, router)
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { ...utils, router, queryClient }
}

export function crearSesion(parcial: Partial<SesionSalida['usuario']> = {}): SesionSalida {
  return {
    usuario: {
      id: '0192f0c0-0000-7000-8000-000000000001',
      nombre_usuario: 'ana.garcia',
      nombre: 'Ana García',
      rol: 'empleado',
      activo: true,
      contrasena_temporal: false,
      bloqueado: false,
      ultimo_acceso_en: null,
      creado_en: '2026-01-10T09:00:00Z',
      ...parcial,
    },
    csrf_token: 'csrf-de-prueba',
    expira_en: '2026-09-27T20:00:00Z',
    inactividad_segundos: 1800,
  }
}

export function problema(status: number, tipo: string, detail: string) {
  return HttpResponse.json(
    { type: `/problemas/${tipo}`, title: 'Error', status, detail },
    { status, headers: { 'Content-Type': 'application/problem+json' } },
  )
}

/** La API responde con la sesión dada (o 401 si es null). */
export function conSesion(sesion: SesionSalida | null): void {
  server.use(
    http.get('*/api/v1/sesion', () =>
      sesion ? HttpResponse.json(sesion) : problema(401, 'no-autenticado', 'Sesión no válida'),
    ),
  )
}

export const CATALOGOS = {
  provincias: [
    { codigo: '18', nombre: 'Granada', nombre_visible: 'Granada' },
    { codigo: '29', nombre: 'Málaga', nombre_visible: 'Málaga' },
  ],
  paises: ['DE', 'ES', 'FR', 'US'],
  paises_nif_iva: ['DE', 'FR'],
  tipos_identificacion: [
    { codigo: 'NIF', descripcion: 'NIF (DNI, NIE o NIF de entidad)', ambito: 'solo_espana' },
    { codigo: '02', descripcion: 'NIF-IVA', ambito: 'paises_nif_iva' },
    { codigo: '03', descripcion: 'Pasaporte', ambito: 'cualquiera' },
    { codigo: '04', descripcion: 'Documento oficial', ambito: 'fuera_de_espana' },
    { codigo: '05', descripcion: 'Certificado de residencia', ambito: 'fuera_de_espana' },
    { codigo: '06', descripcion: 'Otro documento probatorio', ambito: 'fuera_de_espana' },
  ],
} as const

export function conCatalogos(): void {
  server.use(http.get('*/api/v1/catalogos', () => HttpResponse.json(CATALOGOS)))
}

export function crearCliente(parcial: Record<string, unknown> = {}) {
  return {
    id: '0192f0c0-0000-7000-8000-00000000c001',
    tipo: 'particular',
    nombre: 'María López García',
    identificacion_pais: 'ES',
    identificacion_tipo: 'NIF',
    identificacion_numero: '12345678Z',
    localidad: 'Málaga',
    provincia_nombre: 'Málaga',
    telefono: '675 432 198',
    correo: 'maria.lopez@gmail.com',
    activo: true,
    direccion: null,
    codigo_postal: '29005',
    provincia_codigo: '29',
    provincia_texto: null,
    pais_residencia: 'ES',
    observaciones: null,
    version: 1,
    creado_en: '2026-05-27T10:00:00Z',
    creado_por: { id: 'u1', nombre: 'Ana García' },
    actualizado_en: '2026-05-27T10:00:00Z',
    actualizado_por: { id: 'u1', nombre: 'Ana García' },
    ...parcial,
  }
}
