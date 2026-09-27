/** Alias legibles de los esquemas generados desde el OpenAPI. */
import type { components } from './schema.gen'

type Esquemas = components['schemas']

export type SesionSalida = Esquemas['SesionSalida']
export type UsuarioSalida = Esquemas['UsuarioSalida']
export type Rol = UsuarioSalida['rol']
