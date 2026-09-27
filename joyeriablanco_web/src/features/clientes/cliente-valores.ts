/** Valores del formulario de cliente, conversión al cuerpo de la API y reglas de forma. */
import { z } from 'zod'
import type { CatalogosSalida, ClienteEntrada, ClienteSalida } from '../../api/tipos'

// Validación de forma. La de negocio (letra del NIF, estructura NIF-IVA, CP → provincia,
// duplicados…) la decide el servidor (principio VI).
export const esquema = z.object({
  tipo: z.enum(['particular', 'empresa']),
  nombre: z
    .string()
    .trim()
    .min(1, 'Campo obligatorio.')
    .max(120, 'No puede superar 120 caracteres.'),
  identificacion_pais: z.string().length(2, 'Selecciona un país.'),
  identificacion_tipo: z.enum(['NIF', '02', '03', '04', '05', '06']),
  identificacion_numero: z.string().trim().min(1, 'Campo obligatorio.').max(30, 'Demasiado largo.'),
  direccion: z.string().max(200, 'No puede superar 200 caracteres.'),
  codigo_postal: z.string().max(10, 'No puede superar 10 caracteres.'),
  localidad: z.string().max(100, 'No puede superar 100 caracteres.'),
  provincia_codigo: z.string(),
  provincia_texto: z.string().max(100, 'No puede superar 100 caracteres.'),
  pais_residencia: z.string().length(2, 'Selecciona un país.'),
  telefono: z.string().max(30, 'No puede superar 30 caracteres.'),
  correo: z.union([z.literal(''), z.email('Correo electrónico no válido.').max(254)]),
  observaciones: z.string().max(2000, 'No puede superar 2000 caracteres.'),
})
export type ValoresCliente = z.infer<typeof esquema>

export const CAMPOS = Object.keys(esquema.shape) as (keyof ValoresCliente)[]

export function valoresIniciales(cliente?: ClienteSalida): ValoresCliente {
  return {
    tipo: cliente?.tipo ?? 'particular',
    nombre: cliente?.nombre ?? '',
    identificacion_pais: cliente?.identificacion_pais ?? 'ES',
    identificacion_tipo: cliente?.identificacion_tipo ?? 'NIF',
    identificacion_numero: cliente?.identificacion_numero ?? '',
    direccion: cliente?.direccion ?? '',
    codigo_postal: cliente?.codigo_postal ?? '',
    localidad: cliente?.localidad ?? '',
    provincia_codigo: cliente?.provincia_codigo ?? '',
    provincia_texto: cliente?.provincia_texto ?? '',
    pais_residencia: cliente?.pais_residencia ?? 'ES',
    telefono: cliente?.telefono ?? '',
    correo: cliente?.correo ?? '',
    observaciones: cliente?.observaciones ?? '',
  }
}

function nulo(valor: string): string | null {
  const recortado = valor.trim()
  return recortado ? recortado : null
}

export function aCuerpo(v: ValoresCliente): ClienteEntrada {
  return {
    tipo: v.tipo,
    nombre: v.nombre.trim(),
    identificacion_pais: v.identificacion_pais,
    identificacion_tipo: v.identificacion_tipo,
    identificacion_numero: v.identificacion_numero.trim(),
    direccion: nulo(v.direccion),
    codigo_postal: nulo(v.codigo_postal),
    localidad: nulo(v.localidad),
    provincia_codigo: v.pais_residencia === 'ES' ? nulo(v.provincia_codigo) : null,
    provincia_texto: v.pais_residencia === 'ES' ? null : nulo(v.provincia_texto),
    pais_residencia: v.pais_residencia,
    telefono: nulo(v.telefono),
    correo: nulo(v.correo),
    observaciones: nulo(v.observaciones),
  }
}

/** Tipos de identificación admitidos para un país (espejo del `ambito` del catálogo). */
export function tiposPermitidos(pais: string, catalogos: CatalogosSalida) {
  return catalogos.tipos_identificacion.filter(
    (t) =>
      t.ambito === 'cualquiera' ||
      (t.ambito === 'solo_espana' && pais === 'ES') ||
      (t.ambito === 'paises_nif_iva' && catalogos.paises_nif_iva.includes(pais)) ||
      (t.ambito === 'fuera_de_espana' && pais !== 'ES'),
  )
}
