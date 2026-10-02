"""Gestión de clientes (US2–US4; FR-023 a FR-037, FR-055).

El servidor es la fuente de verdad (principio VI): normaliza, valida la identificación con las
reglas oficiales, deriva la provincia del código postal y detecta duplicados y conflictos.
"""

import uuid
from dataclasses import dataclass
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import (
    CampoError,
    ClienteConDocumentos,
    ConflictoVersion,
    DatosNoValidos,
    Duplicado,
    NoEncontrado,
)
from app.core.http import Origen
from app.domain.codigos_postales import provincia_from_codigo_postal
from app.domain.contacto import validate_telefono
from app.domain.identificacion import validate_identificacion
from app.domain.paises import es_codigo_pais
from app.domain.tipos import TipoEvento
from app.models.cliente import Cliente
from app.models.usuario import Usuario
from app.repositories import catalogos as catalogos_repo
from app.repositories import clientes as repo
from app.schemas.cliente import ClienteEdicionEntrada, ClienteEntrada, ClienteExistente
from app.services.auditoria import diff, record_event
from app.services.documentos import ClienteDocumentosChecker

# Campos que se comparan para auditar una edición (FR-021).
CAMPOS_EDITABLES: Final = (
    "tipo",
    "nombre",
    "identificacion_pais",
    "identificacion_tipo",
    "identificacion_numero",
    "direccion",
    "codigo_postal",
    "localidad",
    "provincia_codigo",
    "provincia_texto",
    "pais_residencia",
    "telefono",
    "correo",
    "observaciones",
)


@dataclass(slots=True)
class DatosCliente:
    tipo: str
    nombre: str
    identificacion_pais: str
    identificacion_tipo: str
    identificacion_numero: str
    direccion: str | None
    codigo_postal: str | None
    localidad: str | None
    provincia_codigo: str | None
    provincia_texto: str | None
    pais_residencia: str
    telefono: str | None
    correo: str | None
    observaciones: str | None

    def como_dict(self) -> dict[str, object]:
        return {campo: getattr(self, campo) for campo in CAMPOS_EDITABLES}


def _limpio(valor: str | None) -> str | None:
    if valor is None:
        return None
    recortado = valor.strip()
    return recortado or None


async def _normalizar(db: AsyncSession, entrada: ClienteEntrada) -> DatosCliente:
    """Normaliza y valida todos los campos; acumula los errores por campo."""
    errores: list[CampoError] = []

    nombre = entrada.nombre.strip()
    if not nombre:
        errores.append(CampoError("nombre", "Campo obligatorio."))

    identificacion_pais = entrada.identificacion_pais.upper()
    numero, errores_id = validate_identificacion(
        identificacion_pais, entrada.identificacion_tipo, entrada.identificacion_numero
    )
    errores.extend(errores_id)

    pais_residencia = entrada.pais_residencia.upper()
    if not es_codigo_pais(pais_residencia):
        errores.append(CampoError("pais_residencia", "País no válido."))

    codigo_postal = _limpio(entrada.codigo_postal)
    provincia_codigo = _limpio(entrada.provincia_codigo)
    provincia_texto = _limpio(entrada.provincia_texto)
    if pais_residencia == "ES":
        provincia_texto = None  # no aplica en España (FR-028)
        if codigo_postal is not None:
            try:
                derivada = provincia_from_codigo_postal(codigo_postal)
            except ValueError as exc:
                errores.append(CampoError("codigo_postal", str(exc)))
            else:
                if provincia_codigo is not None and provincia_codigo != derivada:
                    errores.append(
                        CampoError(
                            "provincia_codigo", "La provincia no corresponde al código postal."
                        )
                    )
                provincia_codigo = derivada
        elif provincia_codigo is not None and not await catalogos_repo.get_provincia(
            db, provincia_codigo
        ):
            errores.append(CampoError("provincia_codigo", "Provincia no válida."))
    else:
        provincia_codigo = None  # la lista oficial solo aplica en España

    telefono = _limpio(entrada.telefono)
    if telefono is not None and (motivo := validate_telefono(telefono)):
        errores.append(CampoError("telefono", motivo))

    if errores:
        raise DatosNoValidos(errores=errores)

    correo = _limpio(entrada.correo)
    return DatosCliente(
        tipo=entrada.tipo.value,
        nombre=nombre,
        identificacion_pais=identificacion_pais,
        identificacion_tipo=entrada.identificacion_tipo.value,
        identificacion_numero=numero,
        direccion=_limpio(entrada.direccion),
        codigo_postal=codigo_postal,
        localidad=_limpio(entrada.localidad),
        provincia_codigo=provincia_codigo,
        provincia_texto=provincia_texto,
        pais_residencia=pais_residencia,
        telefono=telefono,
        correo=correo.lower() if correo else None,
        observaciones=_limpio(entrada.observaciones),
    )


def _duplicado(existente: Cliente) -> Duplicado:
    cliente_existente = ClienteExistente(
        id=existente.id, nombre=existente.nombre, activo=existente.activo
    )
    return Duplicado(
        "Ya existe un cliente con esta identificación.",
        extra={"cliente_existente": cliente_existente.model_dump(mode="json")},
    )


async def _comprobar_duplicado(
    db: AsyncSession, datos: DatosCliente, *, excepto: uuid.UUID | None = None
) -> None:
    existente = await repo.get_by_identificacion(
        db,
        pais=datos.identificacion_pais,
        tipo=datos.identificacion_tipo,
        numero=datos.identificacion_numero,
    )
    if existente is not None and existente.id != excepto:
        raise _duplicado(existente)


async def _guardar(db: AsyncSession, cliente: Cliente, datos: DatosCliente, *, nuevo: bool) -> None:
    try:
        if nuevo:
            await repo.add(db, cliente)
        else:
            await repo.save(db, cliente)
    except repo.IdentificacionDuplicada:
        existente = await repo.get_by_identificacion(
            db,
            pais=datos.identificacion_pais,
            tipo=datos.identificacion_tipo,
            numero=datos.identificacion_numero,
        )
        if existente is None:
            raise
        raise _duplicado(existente) from None


async def get_cliente(db: AsyncSession, cliente_id: uuid.UUID) -> Cliente:
    cliente = await repo.get(db, cliente_id)
    if cliente is None:
        raise NoEncontrado("El cliente no existe.")
    return cliente


async def create_cliente(
    db: AsyncSession, entrada: ClienteEntrada, *, actor: Usuario, origen: Origen
) -> Cliente:
    datos = await _normalizar(db, entrada)
    await _comprobar_duplicado(db, datos)
    cliente = Cliente(**datos.como_dict(), creado_por_id=actor.id, actualizado_por_id=actor.id)
    await _guardar(db, cliente, datos, nuevo=True)
    await record_event(
        db,
        TipoEvento.CLIENTE_CREADO,
        origen=origen,
        actor=actor,
        cliente_id=cliente.id,
        detalle={"nombre": cliente.nombre, "tipo": cliente.tipo},
    )
    return cliente


async def update_cliente(
    db: AsyncSession,
    cliente_id: uuid.UUID,
    entrada: ClienteEdicionEntrada,
    *,
    actor: Usuario,
    origen: Origen,
) -> Cliente:
    cliente = await get_cliente(db, cliente_id)
    if cliente.version != entrada.version:
        raise ConflictoVersion
    datos = await _normalizar(db, entrada)
    antes = {campo: getattr(cliente, campo) for campo in CAMPOS_EDITABLES}
    cambios = diff(antes, datos.como_dict())
    if not cambios:
        return cliente
    await _comprobar_duplicado(db, datos, excepto=cliente.id)
    for campo, valor in datos.como_dict().items():
        setattr(cliente, campo, valor)
    cliente.actualizado_por_id = actor.id
    await _guardar(db, cliente, datos, nuevo=False)
    await record_event(
        db,
        TipoEvento.CLIENTE_EDITADO,
        origen=origen,
        actor=actor,
        cliente_id=cliente.id,
        detalle={"cambios": cambios},
    )
    return cliente


# --------------------------------------------------------------------------- listado (US3)


@dataclass(frozen=True, slots=True)
class FiltrosClientes:
    q: str | None = None
    provincia: str | None = None
    tipo: str | None = None
    estado: str = "activos"
    orden: str = "nombre_asc"
    pagina: int = 1
    tamano: int = 25


async def list_clientes(db: AsyncSession, filtros: FiltrosClientes) -> tuple[list[Cliente], int]:
    return await repo.list_clientes(
        db,
        q=filtros.q,
        provincia=filtros.provincia,
        tipo=filtros.tipo,
        estado=filtros.estado,
        orden=filtros.orden,
        pagina=filtros.pagina,
        tamano=filtros.tamano,
    )


async def indicadores(db: AsyncSession) -> tuple[int, int]:
    """Indicadores globales: no dependen de la búsqueda ni de los filtros (FR-034)."""
    return await repo.count_indicadores(db, get_settings().zona_horaria)


# --------------------------------------------------------------------------- ciclo de vida (US4)


async def _cambiar_estado(
    db: AsyncSession,
    cliente_id: uuid.UUID,
    *,
    activo: bool,
    actor: Usuario,
    origen: Origen,
) -> Cliente:
    cliente = await get_cliente(db, cliente_id)
    if cliente.activo is activo:
        return cliente  # idempotente: sin error ni evento nuevo (FR-030)
    cliente.activo = activo
    cliente.actualizado_por_id = actor.id
    await repo.save(db, cliente)
    await record_event(
        db,
        TipoEvento.CLIENTE_REACTIVADO if activo else TipoEvento.CLIENTE_DESACTIVADO,
        origen=origen,
        actor=actor,
        cliente_id=cliente.id,
    )
    return cliente


async def deactivate_cliente(
    db: AsyncSession, cliente_id: uuid.UUID, *, actor: Usuario, origen: Origen
) -> Cliente:
    return await _cambiar_estado(db, cliente_id, activo=False, actor=actor, origen=origen)


async def reactivate_cliente(
    db: AsyncSession, cliente_id: uuid.UUID, *, actor: Usuario, origen: Origen
) -> Cliente:
    return await _cambiar_estado(db, cliente_id, activo=True, actor=actor, origen=origen)


async def delete_cliente(
    db: AsyncSession,
    cliente_id: uuid.UUID,
    *,
    actor: Usuario,
    origen: Origen,
    documentos: ClienteDocumentosChecker,
) -> None:
    """Borrado definitivo, solo sin documentos; la auditoría guarda una instantánea (FR-037)."""
    cliente = await get_cliente(db, cliente_id)
    if await documentos.tiene_documentos(db, cliente.id):
        raise ClienteConDocumentos
    instantanea = {
        "nombre": cliente.nombre,
        "tipo": cliente.tipo,
        "identificacion_pais": cliente.identificacion_pais,
        "identificacion_tipo": cliente.identificacion_tipo,
        "identificacion_numero": cliente.identificacion_numero,
    }
    await repo.delete(db, cliente)
    await record_event(
        db,
        TipoEvento.CLIENTE_BORRADO,
        origen=origen,
        actor=actor,
        cliente_id=cliente_id,
        detalle={"instantanea": instantanea},
    )
