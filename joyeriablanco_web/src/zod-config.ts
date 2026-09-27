/**
 * Debe importarse ANTES que cualquier módulo que construya esquemas de Zod. Zod 4 decide al
 * crear cada esquema si compila validadores con `new Function`; la CSP de producción prohíbe
 * `eval`, así que se desactiva ese modo.
 */
import { z } from 'zod'

z.config({ jitless: true })
