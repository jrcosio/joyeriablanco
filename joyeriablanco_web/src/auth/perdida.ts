/**
 * Pérdida de sesión durante el uso (401 o CSRF no válido): se olvida la caché, se avisa y se vuelve
 * al acceso conservando la ruta (FR-004, FR-011). No se conservan borradores (contracts/ui-rutas.md).
 */
import type { QueryClient } from '@tanstack/react-query'
import type { AnyRouter } from '@tanstack/react-router'
import { setAlPerderSesion } from '../api/client'
import { toast } from '../components/ui/toast-store'
import { olvidarSesion } from './session'

export function configurarPerdidaDeSesion(queryClient: QueryClient, router: AnyRouter): void {
  let enCurso = false
  setAlPerderSesion(() => {
    if (enCurso) return
    enCurso = true
    const volver = router.state.location.href
    olvidarSesion(queryClient)
    toast('Tu sesión ha caducado. Vuelve a identificarte.', 'info')
    void router.navigate({ to: '/acceso', search: { volver } }).finally(() => {
      enCurso = false
    })
  })
}
