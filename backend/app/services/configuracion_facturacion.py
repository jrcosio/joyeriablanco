"""Configuración de facturación y ajuste del contador (US1; FR-001 a FR-004, FR-010, FR-050).

- El IVA admite cualquier tipo de 0 a 99,99. Si el tipo cambia a uno que no está en la lista de
  F-3 §15.1 de hoy, exige confirmarlo, y la auditoría lo deja anotado (research R-20).
- No hay clave de régimen: la fija el sistema en cada factura (R-23). El IBAN es opcional y se
  valida con `domain/iban.py` (R-22).
- Emitir exige emisor completo y modalidad (FR-004). El productor del sistema lo exige `Settings`
  al arrancar en producción (research R-5), así que no figura en `faltan`.
- La modalidad se bloquea en cuanto existe un registro (FR-050, research R-19).
- El contador de la serie ordinaria del año en curso solo se ajusta al alza, con motivo, bajo el
  cerrojo de la cadena y auditado (constitución 2.2.0, «Numeración»; R-7).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.core.errors import (
    CampoError,
    ConflictoVersion,
    ContadorNoAjustable,
    DatosNoValidos,
    ModalidadBloqueada,
    TipoIvaSinConfirmar,
)
from app.core.http import Origen
from app.core.tiempo import hoy
from app.domain.codigos_postales import provincia_from_codigo_postal
from app.domain.contacto import normalize_pie, validate_correo, validate_telefono, validate_web
from app.domain.exenciones import MENCION_EXENCION_ORO_INVERSION
from app.domain.iban import normalize_iban, validate_iban
from app.domain.identificacion import normalize_identificacion, validate_nif
from app.domain.importes import allowed_rates, is_rate_allowed
from app.domain.numeracion import format_num_serie
from app.domain.registro import FECHA_MINIMA_EXPEDICION
from app.domain.tipos import Serie, TipoEvento
from app.models.configuracion_facturacion import ConfiguracionFacturacion
from app.models.usuario import Usuario
from app.repositories import configuracion_facturacion as repo
from app.repositories import contadores, registros
from app.schemas.configuracion_facturacion import (
    AjusteContadorEntrada,
    ConfiguracionFacturacionEntrada,
)
from app.services.auditoria import diff, record_event

CAMPOS_EMISION: Final = (
    ("modalidad", "modalidad"),
    ("emisor.nombre", "emisor_nombre"),
    ("emisor.nif", "emisor_nif"),
    ("emisor.direccion", "emisor_direccion"),
    ("emisor.codigo_postal", "emisor_codigo_postal"),
    ("emisor.localidad", "emisor_localidad"),
)
CAMPOS_AUDITADOS: Final = (
    "iva_por_defecto",
    "modalidad",
    "emisor_nombre",
    "emisor_nif",
    "emisor_direccion",
    "emisor_codigo_postal",
    "emisor_localidad",
    "emisor_provincia_codigo",
    "emisor_iban",
    # Contacto y pie de factura (003, FR-026)
    "emisor_telefono",
    "emisor_correo",
    "emisor_web",
    "pie_factura",
)


def missing_for_emission(config: ConfiguracionFacturacion) -> list[str]:
    return [clave for clave, atributo in CAMPOS_EMISION if getattr(config, atributo) is None]


@dataclass(frozen=True, slots=True)
class EstadoConfiguracion:
    config: ConfiguracionFacturacion
    faltan: list[str]
    proximo_numero: str
    modalidad_bloqueada: bool
    tipos_iva_oficiales: tuple[Decimal, ...]


async def next_num_serie(db: AsyncSession) -> str:
    """Número que recibiría ahora la próxima factura FAC del año en curso (solo informativo)."""
    anio = hoy().year
    return format_num_serie(
        Serie.ORDINARIA, anio, await contadores.last_used(db, Serie.ORDINARIA, anio) + 1
    )


async def get_config(db: AsyncSession) -> EstadoConfiguracion:
    config = await repo.get(db)
    return EstadoConfiguracion(
        config=config,
        faltan=missing_for_emission(config),
        proximo_numero=await next_num_serie(db),
        modalidad_bloqueada=await registros.exists_any(db),
        tipos_iva_oficiales=allowed_rates(hoy()),
    )


@dataclass(frozen=True, slots=True)
class _DatosNormalizados:
    iva_por_defecto: Decimal
    modalidad: str | None
    emisor_nombre: str | None
    emisor_nif: str | None
    emisor_direccion: str | None
    emisor_codigo_postal: str | None
    emisor_localidad: str | None
    emisor_provincia_codigo: str | None
    emisor_iban: str | None
    emisor_telefono: str | None
    emisor_correo: str | None
    emisor_web: str | None
    pie_factura: str | None

    def como_dict(self) -> Mapping[str, object]:
        return {campo: getattr(self, campo) for campo in CAMPOS_AUDITADOS}


def _vacio(valor: str | None) -> str | None:
    return valor or None


def _tipo_iva(entrada: ConfiguracionFacturacionEntrada, actual: Decimal) -> tuple[Decimal, bool]:
    """El tipo normalizado y si queda fuera de la lista oficial de hoy (R-20).

    Solo exige la confirmación si el tipo cambia: guardar otros campos con un tipo ya confirmado
    no la vuelve a pedir.
    """
    tipo = entrada.iva_por_defecto.quantize(Decimal("0.01"))
    if tipo == actual or is_rate_allowed(tipo, hoy()):
        return tipo, False
    if not entrada.confirmar_tipo_iva:
        raise TipoIvaSinConfirmar(
            extra={
                "tipos_oficiales": [
                    format(t.quantize(Decimal("0.01")), "f") for t in allowed_rates(hoy())
                ]
            }
        )
    return tipo, True


def _contacto(
    entrada: ConfiguracionFacturacionEntrada,
    actual: ConfiguracionFacturacion,
    errores: list[CampoError],
) -> tuple[str | None, str | None, str | None, str | None]:
    """Teléfono, correo, web y pie (003, FR-024; R-9). Lo que no viene en la petición se queda."""
    if "contacto" in entrada.model_fields_set:
        contacto = entrada.contacto
        telefono = _vacio(contacto.telefono) if contacto else None
        correo = _vacio(contacto.correo) if contacto else None
        web = _vacio(contacto.web) if contacto else None
        for campo, valor, validar in (
            ("contacto.telefono", telefono, validate_telefono),
            ("contacto.correo", correo, validate_correo),
            ("contacto.web", web, validate_web),
        ):
            if valor is not None and (motivo := validar(valor)):
                errores.append(CampoError(campo, motivo))
        correo = correo.lower() if correo else None
    else:
        telefono, correo, web = actual.emisor_telefono, actual.emisor_correo, actual.emisor_web
    if "pie_factura" in entrada.model_fields_set:
        pie = normalize_pie(entrada.pie_factura) if entrada.pie_factura else None
    else:
        pie = actual.pie_factura
    return telefono, correo, web, pie


def _normalizar(
    entrada: ConfiguracionFacturacionEntrada,
    tipo_iva: Decimal,
    actual: ConfiguracionFacturacion,
) -> _DatosNormalizados:
    errores: list[CampoError] = []
    nif = _vacio(entrada.emisor.nif)
    if nif is not None:
        nif = normalize_identificacion(nif)
        if motivo := validate_nif(nif):
            errores.append(CampoError("emisor.nif", motivo))
    codigo_postal = _vacio(entrada.emisor.codigo_postal)
    provincia = None
    if codigo_postal is not None:
        try:
            provincia = provincia_from_codigo_postal(codigo_postal)
        except ValueError as exc:
            errores.append(CampoError("emisor.codigo_postal", str(exc)))
    iban = _vacio(entrada.emisor.iban)
    if iban is not None:
        iban = normalize_iban(iban)
        if motivo := validate_iban(iban):
            errores.append(CampoError("emisor.iban", motivo))
    telefono, correo, web, pie = _contacto(entrada, actual, errores)
    if errores:
        raise DatosNoValidos(errores=errores)
    return _DatosNormalizados(
        iva_por_defecto=tipo_iva,
        modalidad=entrada.modalidad.value if entrada.modalidad else None,
        emisor_nombre=_vacio(entrada.emisor.nombre),
        emisor_nif=nif,
        emisor_direccion=_vacio(entrada.emisor.direccion),
        emisor_codigo_postal=codigo_postal,
        emisor_localidad=_vacio(entrada.emisor.localidad),
        emisor_provincia_codigo=provincia,
        emisor_iban=iban,
        emisor_telefono=telefono,
        emisor_correo=correo,
        emisor_web=web,
        pie_factura=pie,
    )


async def update_config(
    db: AsyncSession,
    entrada: ConfiguracionFacturacionEntrada,
    *,
    actor: Usuario,
    origen: Origen,
) -> EstadoConfiguracion:
    config = await repo.get(db, for_update=True)
    if config.version != entrada.version:
        raise ConflictoVersion("La configuración ha cambiado desde que la abriste.")
    tipo_iva, fuera_de_lista = _tipo_iva(entrada, config.iva_por_defecto)
    datos = _normalizar(entrada, tipo_iva, config)
    if datos.modalidad != config.modalidad and await registros.exists_any(db):
        raise ModalidadBloqueada
    antes = {campo: getattr(config, campo) for campo in CAMPOS_AUDITADOS}
    cambios = diff(antes, datos.como_dict())
    if cambios:
        for campo, valor in datos.como_dict().items():
            setattr(config, campo, valor)
        config.actualizado_por_id = actor.id
        try:
            await db.flush()
        except StaleDataError as exc:
            raise ConflictoVersion("La configuración ha cambiado desde que la abriste.") from exc
        await db.refresh(config)
        await record_event(
            db,
            TipoEvento.CONFIGURACION_FACTURACION_CAMBIADA,
            origen=origen,
            actor=actor,
            detalle={
                "cambios": cambios,
                # Constancia de que se aceptó el aviso de F-3 §15.1 (FR-001, research R-20).
                **({"tipo_iva_fuera_de_lista": True} if fuera_de_lista else {}),
            },
        )
    return await get_config(db)


@dataclass(frozen=True, slots=True)
class ResultadoAjuste:
    anio: int
    ultimo_usado: int
    proximo_numero: int
    numeros_sin_usar: int
    aplicado: bool


async def adjust_counter(
    db: AsyncSession, entrada: AjusteContadorEntrada, *, actor: Usuario, origen: Origen
) -> ResultadoAjuste:
    anio = hoy().year
    await registros.lock_chain(db)  # mismo orden de cerrojos que la emisión (R-6, R-7)
    ultimo = await contadores.lock_last_used(db, Serie.ORDINARIA, anio)
    if entrada.proximo_numero <= ultimo + 1:
        raise ContadorNoAjustable(
            f"El próximo número debe ser mayor que {ultimo + 1}, que es el que ya corresponde."
        )
    resultado = ResultadoAjuste(
        anio=anio,
        ultimo_usado=ultimo,
        proximo_numero=entrada.proximo_numero,
        numeros_sin_usar=entrada.proximo_numero - ultimo - 1,
        aplicado=not entrada.simular,
    )
    if entrada.simular:
        return resultado
    await contadores.raise_next(db, Serie.ORDINARIA, anio, entrada.proximo_numero)
    await record_event(
        db,
        TipoEvento.CONTADOR_AJUSTADO,
        origen=origen,
        actor=actor,
        detalle={
            "serie": Serie.ORDINARIA.value,
            "anio": anio,
            "ultimo_usado": ultimo,
            "proximo_numero": entrada.proximo_numero,
            "numeros_sin_usar": resultado.numeros_sin_usar,
            "motivo": entrada.motivo,
        },
    )
    return resultado


@dataclass(frozen=True, slots=True)
class Parametros:
    iva_por_defecto: Decimal
    faltan: list[str]
    proximo_numero: str
    hoy: date
    fecha_minima: date | None
    mencion_exencion_oro_inversion: str = MENCION_EXENCION_ORO_INVERSION


async def get_parametros(db: AsyncSession) -> Parametros:
    config = await repo.get(db)
    fecha = hoy()
    return Parametros(
        iva_por_defecto=config.iva_por_defecto,
        faltan=missing_for_emission(config),
        proximo_numero=await next_num_serie(db),
        hoy=fecha,
        fecha_minima=FECHA_MINIMA_EXPEDICION,
    )
