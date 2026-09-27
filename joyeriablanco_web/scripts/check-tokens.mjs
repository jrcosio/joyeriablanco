/**
 * Conformidad con el sistema de diseño (constitución 1.1.0, SC-009): colores y radios solo
 * desde los tokens de src/styles/tokens.css. Falla si encuentra en src/:
 *   - colores literales (#rgb, #rrggbb, rgb(), rgba(), hsl(), oklch()…),
 *   - clases de radio distintas de `rounded-none`,
 *   - estilos `borderRadius` en línea.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'

const RAIZ = path.resolve(import.meta.dirname, '..', 'src')
const EXCLUIDOS = new Set(['styles/tokens.css', 'routeTree.gen.ts', 'api/schema.gen.ts'])
const EXTENSIONES = /\.(tsx?|css)$/

const REGLAS = [
  { nombre: 'color hexadecimal', patron: /(?<![\w&/-])#[0-9a-fA-F]{3,8}\b/g },
  { nombre: 'color funcional', patron: /\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\(/g },
  { nombre: 'radio distinto de 0', patron: /\brounded(?:-(?!none\b)[\w[\]./-]+)?\b/g },
  { nombre: 'borderRadius en línea', patron: /borderRadius/g },
]

function ficheros(dir) {
  return readdirSync(dir).flatMap((nombre) => {
    const ruta = path.join(dir, nombre)
    return statSync(ruta).isDirectory() ? ficheros(ruta) : EXTENSIONES.test(nombre) ? [ruta] : []
  })
}

const errores = []
for (const fichero of ficheros(RAIZ)) {
  const relativo = path.relative(RAIZ, fichero).split(path.sep).join('/')
  if (EXCLUIDOS.has(relativo) || relativo.includes('.test.')) continue
  const lineas = readFileSync(fichero, 'utf8').split('\n')
  lineas.forEach((linea, i) => {
    if (linea.trim().startsWith('//') || linea.trim().startsWith('*')) return
    for (const { nombre, patron } of REGLAS) {
      for (const coincidencia of linea.matchAll(patron)) {
        errores.push(`${relativo}:${i + 1}: ${nombre} «${coincidencia[0]}»`)
      }
    }
  })
}

if (errores.length) {
  console.error(`✘ ${errores.length} infracciones del sistema de diseño:\n${errores.join('\n')}`)
  process.exit(1)
}
console.log('✔ Colores y radios solo desde los tokens de DESIGN.md (src/styles/tokens.css).')
