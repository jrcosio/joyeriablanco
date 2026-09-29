"""Datos de ejemplo ficticios para desarrollo y E2E (US7; FR-045, research R-19).

- Se niega a ejecutarse en producción.
- Es idempotente: si ya existe el usuario `admin.demo`, no hace nada.
- Los NIF de particulares llevan la letra calculada con el algoritmo oficial. Los de empresa solo
  cumplen la estructura: el algoritmo de su carácter de control no está publicado (R-20.2).
- Todo pasa por los servicios, así que cada alta queda validada y auditada. Las facturas se
  emiten con `emision.emit_factura`, de modo que sus registros quedan encadenados (002, R-16).
"""

import random
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import Duplicado, SinPermiso
from app.core.http import Origen
from app.core.security import hash_password
from app.core.tiempo import ahora, hoy
from app.domain.tipos import (
    CLAVE_REGIMEN_GENERAL,
    CausaRectificacion,
    Modalidad,
    MotivoModificacion,
    Rol,
    TipoCliente,
    TipoIdentificacion,
)
from app.models.cliente import Cliente
from app.models.factura import Factura
from app.models.usuario import Usuario
from app.repositories import configuracion_facturacion as configuracion_repo
from app.repositories import usuarios as usuarios_repo
from app.schemas.cliente import ClienteEntrada
from app.schemas.configuracion_facturacion import (
    ConfiguracionFacturacionEntrada,
    DatosEmisorEntrada,
)
from app.services import borradores as borradores_srv
from app.services import clientes as clientes_srv
from app.services import configuracion_facturacion, emision, usuarios

if TYPE_CHECKING:
    from faker import Faker

MARCADOR: Final = "(EJEMPLO)"
ORIGEN: Final = Origen(ip=None, agente="joyeria cargar-datos-ejemplo")
_LETRAS_DNI: Final = "TRWAGMYFPDXBNJZSQVHLCKE"

USUARIOS_DEMO: Final = (
    ("admin.demo", "Luis Martín", Rol.ADMINISTRADOR),
    ("empleado.demo", "Lucía Moreno", Rol.EMPLEADO),
    ("vendedor.demo", "Pablo Ortega", Rol.EMPLEADO),
)

LOCALIDADES_ES: Final = (
    ("18001", "Granada"),
    ("18600", "Motril"),
    ("29001", "Málaga"),
    ("29600", "Marbella"),
    ("29620", "Torremolinos"),
    ("14001", "Córdoba"),
    ("41001", "Sevilla"),
    ("41700", "Dos Hermanas"),
    ("04001", "Almería"),
    ("23001", "Jaén"),
    ("11001", "Cádiz"),
    ("11401", "Jerez de la Frontera"),
    ("21001", "Huelva"),
    ("28001", "Madrid"),
    ("08001", "Barcelona"),
    ("46001", "Valencia"),
    ("03001", "Alicante"),
    ("30001", "Murcia"),
    ("48001", "Bilbao"),
    ("15001", "A Coruña"),
    ("50001", "Zaragoza"),
    ("35001", "Las Palmas de Gran Canaria"),
    ("07001", "Palma"),
)

# (país, CP, localidad, región, tipo de identificación, generador de número)
EXTRANJEROS: Final = (
    ("FR", "13001", "Marseille", "Provence-Alpes-Côte d'Azur", TipoIdentificacion.NIF_IVA),
    ("DE", "10115", "Berlin", "Berlin", TipoIdentificacion.NIF_IVA),
    ("PT", "1100-148", "Lisboa", "Lisboa", TipoIdentificacion.NIF_IVA),
    ("IT", "20121", "Milano", "Lombardia", TipoIdentificacion.NIF_IVA),
    ("US", "10001", "New York", "New York", TipoIdentificacion.PASAPORTE),
    ("GB", "SW1A 1AA", "London", "England", TipoIdentificacion.PASAPORTE),
    ("MX", "06600", "Ciudad de México", "CDMX", TipoIdentificacion.PASAPORTE),
)
_NIF_IVA_CUERPO: Final = {"FR": 11, "DE": 9, "PT": 9, "IT": 11}

# Emisor ficticio: el NIF de entidad solo cumple la estructura (R-20.2 de 001).
EMISOR_DEMO: Final = DatosEmisorEntrada(
    nombre="Joyería Blanco (demo)",
    nif="B18000000",
    direccion="Calle Reyes Católicos, 1",
    codigo_postal="18001",
    localidad="Granada",
)
DIAS_FACTURAS: Final = 182  # unos 6 meses (R-16)

# (descripción, precio mínimo, precio máximo) sin IVA, en euros.
ARTICULOS: Final = (
    ("Anillo de oro amarillo de 18 k", 180, 1800),
    ("Alianza de oro blanco", 250, 900),
    ("Pendientes de plata de ley con circonitas", 35, 150),
    ("Collar de perlas cultivadas", 200, 1200),
    ("Pulsera de oro rosa", 150, 800),
    ("Reloj automático de acero", 300, 2500),
    ("Colgante de oro con esmeralda", 400, 2200),
    ("Grabado personalizado", 10, 40),
    ("Ajuste de talla de anillo", 20, 60),
    ("Limpieza y pulido ultrasónico", 15, 45),
    ("Cambio de pila de reloj", 8, 20),
    ("Reparación de cierre", 15, 50),
)


@dataclass(slots=True)
class ResumenCarga:
    clientes_creados: int = 0
    facturas_emitidas: int = 0
    correcciones: int = 0
    borradores_creados: int = 0
    ya_cargados: bool = False
    contrasenas_temporales: dict[str, str] = field(default_factory=dict)


def _dni(rng: random.Random) -> str:
    numero = rng.randrange(10_000_000, 99_999_999)
    return f"{numero:08d}{_LETRAS_DNI[numero % 23]}"


def _nie(rng: random.Random) -> str:
    prefijo = rng.choice("XYZ")
    numero = rng.randrange(0, 9_999_999)
    valor = int(f"{'XYZ'.index(prefijo)}{numero:07d}")
    return f"{prefijo}{numero:07d}{_LETRAS_DNI[valor % 23]}"


def _nif_entidad(rng: random.Random) -> str:
    return f"{rng.choice('ABF')}{rng.randrange(0, 9_999_999):07d}{rng.randrange(10)}"


def _telefono(rng: random.Random) -> str:
    primero = rng.choice("6796")
    resto = f"{rng.randrange(0, 99_999_999):08d}"
    return f"{primero}{resto[:2]} {resto[2:5]} {resto[5:]}"


def _slug(texto: str) -> str:
    tabla = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
    return "".join(c for c in texto.translate(tabla).lower() if c.isalnum() or c == ".")


def _entrada(rng: random.Random, fake: "Faker", indice: int) -> ClienteEntrada:
    tirada = rng.random()
    observaciones = f"{MARCADOR} Cliente ficticio n.º {indice + 1}."
    if tirada < 0.08:  # extranjero
        pais, cp, localidad, region, tipo_id = rng.choice(EXTRANJEROS)
        if tipo_id is TipoIdentificacion.NIF_IVA:
            longitud = _NIF_IVA_CUERPO[pais]
            numero = "".join(str(rng.randrange(1, 10)) for _ in range(longitud))
            nombre = f"{fake.last_name()} {rng.choice(['SARL', 'GmbH', 'Lda.', 'S.r.l.'])}"
            tipo = TipoCliente.EMPRESA
        else:
            numero = f"{rng.choice('ABCKLP')}{rng.randrange(1_000_000, 99_999_999)}"
            nombre = f"{fake.first_name()} {fake.last_name()}"
            tipo = TipoCliente.PARTICULAR
        return ClienteEntrada(
            tipo=tipo,
            nombre=nombre,
            identificacion_pais=pais,
            identificacion_tipo=tipo_id,
            identificacion_numero=numero,
            codigo_postal=cp,
            localidad=localidad,
            provincia_texto=region,
            pais_residencia=pais,
            telefono=f"+{rng.randrange(30, 99)} {rng.randrange(100_000_000, 999_999_999)}",
            correo=f"{_slug(nombre.split()[0])}{indice}@example.com",
            observaciones=observaciones,
        )

    cp, localidad = rng.choice(LOCALIDADES_ES)
    if tirada < 0.30:  # empresa española
        nombre = (
            f"{rng.choice(['Joyería', 'Relojería', 'Platería', 'Orfebrería', 'Distribuciones'])} "
            f"{fake.last_name()}{rng.choice([' S.L.', ' S.A.', ''])}"
        )
        tipo, numero = TipoCliente.EMPRESA, _nif_entidad(rng)
        correo = f"info@{_slug(nombre.split()[1])}{indice}.example.com"
    else:  # particular
        nombre = f"{fake.first_name()} {fake.last_name()} {fake.last_name()}"
        tipo = TipoCliente.PARTICULAR
        numero = _nie(rng) if rng.random() < 0.15 else _dni(rng)
        correo = f"{_slug(nombre.split()[0])}.{_slug(nombre.split()[1])}{indice}@example.com"
    return ClienteEntrada(
        tipo=tipo,
        nombre=nombre,
        identificacion_pais="ES",
        identificacion_tipo=TipoIdentificacion.NIF,
        identificacion_numero=numero,
        direccion=f"{fake.street_name()} {rng.randrange(1, 120)}",
        codigo_postal=cp,
        localidad=localidad,
        pais_residencia="ES",
        telefono=_telefono(rng),
        correo=correo,
        observaciones=observaciones,
    )


async def _crear_usuarios(
    db: AsyncSession, contrasena_demo: str | None, resumen: ResumenCarga
) -> list[Usuario]:
    """Crea los usuarios de ejemplo. El primero es el administrador."""
    creados: list[Usuario] = []
    for nombre_usuario, nombre, rol in USUARIOS_DEMO:
        usuario, temporal = await usuarios.create_usuario(
            db,
            nombre_usuario=nombre_usuario,
            nombre=nombre,
            rol=rol,
            actor=creados[0] if creados else None,
            origen=ORIGEN,
        )
        if contrasena_demo:
            usuario.hash_contrasena = hash_password(contrasena_demo)
            usuario.contrasena_temporal = False
            usuario.contrasena_temporal_expira_en = None
        else:
            resumen.contrasenas_temporales[nombre_usuario] = temporal
        creados.append(usuario)
    await db.flush()
    return creados


async def _configurar_facturacion(db: AsyncSession, admin: Usuario) -> None:
    """Configuración demo (R-16): IVA general, emisor ficticio y modalidad VERI*FACTU."""
    config = await configuracion_repo.get(db)
    await configuracion_facturacion.update_config(
        db,
        ConfiguracionFacturacionEntrada.model_validate(
            {
                "version": config.version,
                "iva_por_defecto": "21.00",
                "clave_regimen": CLAVE_REGIMEN_GENERAL,
                "modalidad": Modalidad.VERIFACTU,
                "emisor": EMISOR_DEMO,
            }
        ),
        actor=admin,
        origen=ORIGEN,
    )


def _lineas(rng: random.Random) -> tuple[emision.DatosLinea, ...]:
    lineas = []
    for descripcion, minimo, maximo in rng.sample(ARTICULOS, k=rng.choice((1, 1, 2, 2, 3))):
        centimos = rng.randrange(minimo * 100, maximo * 100 + 1)
        lineas.append(
            emision.DatosLinea(
                unidades=Decimal(rng.choice((1, 1, 1, 2))),
                descripcion=descripcion,
                precio_unitario=Decimal(centimos) / 100,
            )
        )
    return tuple(lineas)


async def _emitir_facturas(
    db: AsyncSession,
    rng: random.Random,
    *,
    cantidad: int,
    emisores: list[Usuario],
    clientes: list[Cliente],
) -> list[Factura]:
    """Emite `cantidad` facturas de los últimos meses, en orden de fecha (FR-018)."""
    facturables = [c for c in clientes if c.activo and c.direccion and c.localidad]
    if not facturables or cantidad == 0:
        return []
    hoy_madrid = hoy()
    fechas: list[date] = sorted(
        hoy_madrid - timedelta(days=rng.randrange(0, DIAS_FACTURAS)) for _ in range(cantidad)
    )
    emitidas: list[Factura] = []
    for fecha in fechas:
        factura, _ = await emision.emit_factura(
            db,
            emision.DatosFactura(
                fecha_expedicion=fecha,
                cliente_id=rng.choice(facturables).id,
                lineas=_lineas(rng),
            ),
            actor=rng.choice(emisores),
            origen=ORIGEN,
            clave=uuid.UUID(int=rng.getrandbits(128), version=4),
        )
        emitidas.append(factura)
    return emitidas


async def _corregir(
    db: AsyncSession, rng: random.Random, *, facturas: list[Factura], admin: Usuario
) -> int:
    """Correcciones de ejemplo sobre facturas distintas (T069): una anulación, una reemisión, una
    rectificativa R4, una devolución total R1 y una rectificativa anulada."""
    if len(facturas) < 5:
        return 0
    elegidas = rng.sample(facturas, k=5)

    def clave() -> uuid.UUID:
        return uuid.UUID(int=rng.getrandbits(128), version=4)

    async def modificar(
        factura: Factura,
        motivo: MotivoModificacion,
        causa: CausaRectificacion | None,
        lineas: tuple[emision.DatosLinea, ...],
    ) -> Factura:
        nueva, _ = await emision.modify_factura(
            db,
            factura.id,
            emision.DatosModificacion(
                motivo=motivo,
                causa=causa,
                motivo_texto=f"{MARCADOR} Corrección de ejemplo.",
                cliente_id=factura.cliente_id,
                lineas=lineas,
            ),
            actor=admin,
            origen=ORIGEN,
            clave=clave(),
        )
        return nueva

    async def anular(factura: Factura) -> None:
        await emision.anular_factura(
            db,
            factura.id,
            motivo_texto=f"{MARCADOR} Emitida por error.",
            actor=admin,
            origen=ORIGEN,
            clave=clave(),
        )

    anulada, reemitida, r4, devuelta, a_anular = elegidas
    await anular(anulada)
    await modificar(reemitida, MotivoModificacion.NO_DEBIO_EMITIRSE, None, _lineas(rng))
    await modificar(
        r4, MotivoModificacion.FACTURA_ENTREGADA, CausaRectificacion.ERROR_DATOS, _lineas(rng)
    )
    await modificar(
        devuelta, MotivoModificacion.FACTURA_ENTREGADA, CausaRectificacion.DEVOLUCION_O_PRECIO, ()
    )
    rectificativa = await modificar(
        a_anular, MotivoModificacion.FACTURA_ENTREGADA, CausaRectificacion.ERROR_DATOS, _lineas(rng)
    )
    await anular(rectificativa)
    return 6


async def _crear_borradores(
    db: AsyncSession,
    rng: random.Random,
    *,
    cantidad: int,
    autores: list[Usuario],
    clientes: list[Cliente],
) -> int:
    """Borradores de hoy, el primero sin cliente (T061): se guardan con el servicio, que calcula
    sus totales previstos y los audita."""
    activos = [c for c in clientes if c.activo]
    for indice in range(cantidad):
        await borradores_srv.create_borrador(
            db,
            borradores_srv.DatosBorrador(
                fecha_expedicion=hoy(),
                cliente_id=None if indice == 0 or not activos else rng.choice(activos).id,
                lineas=_lineas(rng),
            ),
            actor=rng.choice(autores),
            origen=ORIGEN,
        )
    return cantidad


async def cargar(
    db: AsyncSession,
    *,
    clientes: int = 40,
    facturas: int = 50,
    borradores: int = 5,
    contrasena_demo: str | None = None,
    semilla: int = 2026,
) -> ResumenCarga:
    if get_settings().es_produccion:
        msg = "La carga de datos de ejemplo no está permitida en producción."
        raise SinPermiso(msg)
    resumen = ResumenCarga()
    if await usuarios_repo.get_by_nombre_usuario(db, "admin.demo") is not None:
        resumen.ya_cargados = True
        return resumen

    from faker import Faker

    fake = Faker("es_ES")
    fake.seed_instance(semilla)
    rng = random.Random(semilla)  # noqa: S311 — datos ficticios, no criptográficos
    demo = await _crear_usuarios(db, contrasena_demo, resumen)
    admin = demo[0]

    momento = ahora()
    indice = 0
    creados: list[Cliente] = []
    while resumen.clientes_creados < clientes:
        entrada = _entrada(rng, fake, indice)
        indice += 1
        try:
            cliente = await clientes_srv.create_cliente(db, entrada, actor=admin, origen=ORIGEN)
        except Duplicado:
            continue
        cliente.creado_en = momento - timedelta(
            days=rng.randrange(0, 720), minutes=rng.randrange(1440)
        )
        cliente.actualizado_en = cliente.creado_en
        cliente.activo = rng.random() >= 0.1
        creados.append(cliente)
        resumen.clientes_creados += 1
        if resumen.clientes_creados % 500 == 0:
            await db.flush()
    await db.flush()

    await _configurar_facturacion(db, admin)
    emitidas = await _emitir_facturas(db, rng, cantidad=facturas, emisores=demo, clientes=creados)
    resumen.facturas_emitidas = len(emitidas)
    resumen.correcciones = await _corregir(db, rng, facturas=emitidas, admin=admin)
    resumen.borradores_creados = await _crear_borradores(
        db, rng, cantidad=borradores, autores=demo, clientes=creados
    )
    return resumen
