import { desdeApi, formatearCantidad, formatearEuros } from '../../lib/dinero'

interface LineaGuardada {
  orden: number
  unidades: string
  descripcion: string
  precio_unitario: string
  importe: string
}

/** Líneas de un documento emitido, en solo lectura (factura o presupuesto; 005, R-13). */
export function LineasSoloLectura({
  lineas,
  titulo,
}: {
  lineas: readonly LineaGuardada[]
  /** Texto accesible de la tabla, p. ej. «Líneas del presupuesto PRE-2026-0003». */
  titulo: string
}) {
  return (
    <div className="overflow-x-auto border border-primary-container/18 bg-surface-container-low">
      <table className="w-full">
        <caption className="sr-only">{titulo}</caption>
        <thead className="bg-surface-container">
          <tr className="label-md text-on-surface-variant">
            <th scope="col" className="px-4 py-3 text-right">
              Unidades
            </th>
            <th scope="col" className="px-4 py-3 text-left">
              Descripción
            </th>
            <th scope="col" className="px-4 py-3 text-right">
              Precio unitario
            </th>
            <th scope="col" className="px-4 py-3 text-right">
              Importe
            </th>
          </tr>
        </thead>
        <tbody>
          {lineas.map((linea) => (
            <tr key={linea.orden} className="border-t border-primary-container/10 body-md">
              <td className="px-4 py-3 text-right tabular-nums">
                {formatearCantidad(desdeApi(linea.unidades))}
              </td>
              <td className="px-4 py-3">{linea.descripcion}</td>
              <td className="px-4 py-3 text-right tabular-nums">
                {formatearEuros(desdeApi(linea.precio_unitario))}
              </td>
              <td className="px-4 py-3 text-right tabular-nums">
                {formatearEuros(desdeApi(linea.importe))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
