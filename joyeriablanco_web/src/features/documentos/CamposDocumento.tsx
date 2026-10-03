import { useWatch, type Control } from 'react-hook-form'
import { calcularTotales, desdeApi } from '../../lib/dinero'
import { lineasCalculo, type ConLineas } from './documento-valores'
import { TotalesDocumento } from './TotalesDocumento'

/** Una sección del formulario del documento, con su título (002, FR-037; 005, FR-026). */
export function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h3 className="title-lg text-on-surface">{titulo}</h3>
      {children}
    </section>
  )
}

/** Dato de solo lectura con el aspecto de un campo (p. ej. el número, que asigna el servidor). */
export function SoloLectura({
  etiqueta,
  valor,
  ayuda,
}: {
  etiqueta: string
  valor: string
  ayuda?: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="label-md text-on-surface-variant">{etiqueta}</span>
      <span className="flex h-11 items-center border border-on-surface/12 bg-surface-container px-3 body-md text-on-surface-variant tabular-nums">
        {valor}
      </span>
      {ayuda ? <span className="body-sm text-on-surface-variant">{ayuda}</span> : null}
    </div>
  )
}

/**
 * Totales previstos en el navegador (002, R-11). Tras guardar mandan los del servidor. Con «Sin
 * IVA (oro de inversión)», sin tipo ni cuota y con la mención de la exención (FR-052).
 */
export function PrevisualizacionTotales<T extends ConLineas>({
  control: controlFormulario,
  ivaPorDefecto,
  mencionExencion,
  titulo,
}: {
  control: Control<T>
  ivaPorDefecto: string
  mencionExencion: string
  titulo?: string
}) {
  // Mismos campos en los dos formularios (`ConLineas`), como en `LineasDocumento`.
  const control = controlFormulario as unknown as Control<ConLineas>
  const lineas = useWatch({ control, name: 'lineas' })
  const exenta = useWatch({ control, name: 'oro_inversion' })
  const tipoIva = exenta ? null : ivaPorDefecto
  const totales = calcularTotales(
    lineasCalculo(lineas),
    tipoIva === null ? null : desdeApi(tipoIva),
  )
  return (
    <TotalesDocumento
      {...totales}
      tipoIva={tipoIva}
      mencion={exenta ? mencionExencion : null}
      {...(titulo ? { titulo } : {})}
    />
  )
}
