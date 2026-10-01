import { useCallback, useState } from 'react'

/**
 * Clave de operación (`Idempotency-Key`) para emitir, modificar y anular (FR-047; R-18).
 *
 * Se genera una vez por modal y se REUTILIZA en los reintentos (doble clic, corte de red): el
 * servidor devuelve entonces el resultado de la primera petición en lugar de emitir otra
 * factura. Solo se renueva cuando la operación ha terminado con éxito.
 */
export function useClaveOperacion(): { clave: string; renovar: () => void } {
  const [clave, setClave] = useState(() => crypto.randomUUID())
  const renovar = useCallback(() => {
    setClave(crypto.randomUUID())
  }, [])
  return { clave, renovar }
}
