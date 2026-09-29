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
export type ClienteResumenSalida = Esquemas['ClienteResumenSalida']
export type PaginaClientes = Esquemas['Pagina_ClienteResumenSalida_']
export type IndicadoresSalida = Esquemas['IndicadoresSalida']
export type UsuarioAltaEntrada = Esquemas['UsuarioAltaEntrada']
export type UsuarioConContrasenaTemporal = Esquemas['UsuarioConContrasenaTemporalSalida']
export type EventoSalida = Esquemas['EventoSalida']
export type PaginaEventos = Esquemas['Pagina_EventoSalida_']
export type TipoEvento = EventoSalida['tipo']

export type ConfiguracionFacturacionSalida = Esquemas['ConfiguracionFacturacionSalida']
export type ConfiguracionFacturacionEntrada = Esquemas['ConfiguracionFacturacionEntrada']
export type Modalidad = NonNullable<ConfiguracionFacturacionEntrada['modalidad']>
export type AjusteContadorEntrada = Esquemas['AjusteContadorEntrada']
export type AjusteContadorSalida = Esquemas['AjusteContadorSalida']
export type ParametrosFacturacionSalida = Esquemas['ParametrosFacturacionSalida']
