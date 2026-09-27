/** Alias legibles de los esquemas generados desde el OpenAPI. */
import type { components } from './schema.gen'

type Esquemas = components['schemas']

export type SesionSalida = Esquemas['SesionSalida']
export type UsuarioSalida = Esquemas['UsuarioSalida']
export type Rol = UsuarioSalida['rol']

export type ClienteSalida = Esquemas['ClienteSalida']
export type ClienteEntrada = Esquemas['ClienteEntrada']
export type ClienteEdicionEntrada = Esquemas['ClienteEdicionEntrada']
export type CatalogosSalida = Esquemas['CatalogosSalida']
export type TipoIdentificacion = ClienteEntrada['identificacion_tipo']
export type TipoCliente = ClienteEntrada['tipo']
