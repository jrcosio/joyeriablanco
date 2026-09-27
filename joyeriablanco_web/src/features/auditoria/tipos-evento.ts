import type { TipoEvento } from '../../api/tipos'

/** Nombre en español de cada tipo de evento de auditoría. */
export const TIPOS_EVENTO: Record<TipoEvento, string> = {
  acceso_correcto: 'Acceso correcto',
  acceso_fallido: 'Acceso fallido',
  acceso_bloqueado: 'Cuenta bloqueada',
  acceso_limitado: 'Acceso limitado por origen',
  cierre_sesion: 'Cierre de sesión',
  contrasena_cambiada: 'Contraseña cambiada',
  contrasena_restablecida: 'Contraseña restablecida',
  usuario_creado: 'Usuario creado',
  usuario_rol_cambiado: 'Rol cambiado',
  usuario_desactivado: 'Usuario desactivado',
  usuario_reactivado: 'Usuario reactivado',
  usuario_eliminado: 'Usuario eliminado',
  cliente_creado: 'Cliente creado',
  cliente_editado: 'Cliente editado',
  cliente_desactivado: 'Cliente desactivado',
  cliente_reactivado: 'Cliente reactivado',
  cliente_borrado: 'Cliente borrado',
}
