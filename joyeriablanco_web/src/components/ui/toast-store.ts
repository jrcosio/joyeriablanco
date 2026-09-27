/** Almacén de avisos breves (FR-058); la región visual está en Toast.tsx. */
export type ToastTone = 'success' | 'error' | 'info'

export interface ToastItem {
  id: number
  message: string
  tone: ToastTone
}

const DURACION_MS = 5000
let siguienteId = 1
let avisos: ToastItem[] = []
const suscriptores = new Set<() => void>()

function emitir() {
  for (const suscriptor of suscriptores) suscriptor()
}

export function cerrarAviso(id: number): void {
  avisos = avisos.filter((a) => a.id !== id)
  emitir()
}

/** Aviso breve de nivel 3 (FR-058). */
export function toast(message: string, tone: ToastTone = 'success'): void {
  const id = siguienteId++
  avisos = [...avisos, { id, message, tone }]
  emitir()
  setTimeout(() => {
    cerrarAviso(id)
  }, DURACION_MS)
}

export function suscribir(callback: () => void) {
  suscriptores.add(callback)
  return () => {
    suscriptores.delete(callback)
  }
}

export function getAvisos(): readonly ToastItem[] {
  return avisos
}
