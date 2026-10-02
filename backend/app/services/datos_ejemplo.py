"""Datos de ejemplo ficticios para desarrollo y E2E (US7; FR-045, research R-19).

- Se niega a ejecutarse en producción.
- Es idempotente: si ya existe el usuario `admin.demo`, no hace nada.
- Los NIF de particulares llevan la letra calculada con el algoritmo oficial. Los de empresa solo
  cumplen la estructura: el algoritmo de su carácter de control no está publicado (R-20.2).
- Todo pasa por los servicios, así que cada alta queda validada y auditada. Las facturas se
  emiten con `emision.emit_factura`, de modo que sus registros quedan encadenados (002, R-16).
- Los presupuestos (005, FR-036) se emiten, convierten, modifican y anulan también con sus
  servicios. Las conversiones emiten facturas de hoy, encadenadas como las demás.
"""

import random
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import Duplicado, SinPermiso
from app.core.http import Origen
from app.core.security import hash_password
from app.core.tiempo import ahora, hoy
from app.domain.tipos import (
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
from app.repositories import presupuestos as presupuestos_repo
from app.repositories import registros as registros_repo
from app.repositories import usuarios as usuarios_repo
from app.schemas.cliente import ClienteEntrada
from app.schemas.configuracion_facturacion import (
    ConfiguracionFacturacionEntrada,
    ContactoEntrada,
    DatosEmisorEntrada,
)
from app.services import borradores as borradores_srv
from app.services import borradores_presupuesto as borradores_presupuesto_srv
from app.services import clientes as clientes_srv
from app.services import configuracion_facturacion, conversion, emision, presupuestos, usuarios

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
    iban="ES91 2100 0418 4502 0005 1332",  # IBAN de ejemplo con dígito de control válido (R-22)
)
# Contacto y pie de factura ficticios (003, FR-032): dominio `.demo`, que nunca existe.
CONTACTO_DEMO: Final = ContactoEntrada(
    telefono="+34 900 000 000", correo="info@joyeriablanco.demo", web="joyeriablanco.demo"
)
PIE_DEMO: Final = (
    "Texto de ejemplo. Responsable del tratamiento: Joyería Blanco (demo). Sus datos se usan solo "
    "para la facturación y se conservan durante los plazos legales.\n"
    "Puede ejercer sus derechos de acceso, rectificación y supresión en la tienda."
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
# Oro de inversión (F-11, art. 140): van en facturas sin IVA (FR-052, R-21).
ARTICULOS_ORO_INVERSION: Final = (
    ("Lingote de oro de 50 g, ley 999,9", 3500, 4200),
    ("Moneda de oro Krugerrand de 1 oz", 2300, 2900),
)
CADA_ORO_INVERSION: Final = 25  # una de cada 25 facturas de ejemplo


@dataclass(slots=True)
class ResumenCarga:
    clientes_creados: int = 0
    facturas_emitidas: int = 0
    correcciones: int = 0
    borradores_creados: int = 0
    presupuestos: int = 0
    borradores_presupuesto: int = 0
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
    """Configuración demo (R-16): IVA general, emisor ficticio con IBAN, modalidad VERI*FACTU, y
    contacto y pie de factura ficticios (003, FR-032)."""
    config = await configuracion_repo.get(db)
    await configuracion_facturacion.update_config(
        db,
        ConfiguracionFacturacionEntrada.model_validate(
            {
                "version": config.version,
                "iva_por_defecto": "21.00",
                "modalidad": Modalidad.VERIFACTU,
                "emisor": EMISOR_DEMO,
                "contacto": CONTACTO_DEMO,
                "pie_factura": PIE_DEMO,
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


def _lineas_oro(rng: random.Random) -> tuple[emision.DatosLinea, ...]:
    descripcion, minimo, maximo = rng.choice(ARTICULOS_ORO_INVERSION)
    centimos = rng.randrange(minimo * 100, maximo * 100 + 1)
    return (
        emision.DatosLinea(
            unidades=Decimal(1), descripcion=descripcion, precio_unitario=Decimal(centimos) / 100
        ),
    )


def _es_oro(indice: int) -> bool:
    return indice % CADA_ORO_INVERSION == CADA_ORO_INVERSION // 2


async def _emitir_facturas(
    db: AsyncSession,
    rng: random.Random,
    *,
    cantidad: int,
    emisores: list[Usuario],
    clientes: list[Cliente],
) -> list[Factura]:
    """Emite `cantidad` facturas de los últimos meses, en orden de fecha (FR-018). Una de cada 25
    es de oro de inversión, sin IVA (R-21)."""
    facturables = [c for c in clientes if c.activo and c.direccion and c.localidad]
    if not facturables or cantidad == 0:
        return []
    hoy_madrid = hoy()
    fechas: list[date] = sorted(
        hoy_madrid - timedelta(days=rng.randrange(0, DIAS_FACTURAS)) for _ in range(cantidad)
    )
    emitidas: list[Factura] = []
    for indice, fecha in enumerate(fechas):
        oro = _es_oro(indice)
        factura, _ = await emision.emit_factura(
            db,
            emision.DatosFactura(
                fecha_expedicion=fecha,
                cliente_id=rng.choice(facturables).id,
                lineas=_lineas_oro(rng) if oro else _lineas(rng),
                oro_inversion=oro,
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
    """Borradores de hoy, el primero sin cliente (T061) y, si hay más de uno, el último de oro de
    inversión (R-21): se guardan con el servicio, que calcula sus totales previstos y los audita."""
    activos = [c for c in clientes if c.activo]
    for indice in range(cantidad):
        oro = cantidad > 1 and indice == cantidad - 1
        await borradores_srv.create_borrador(
            db,
            borradores_srv.DatosBorrador(
                fecha_expedicion=hoy(),
                cliente_id=None if indice == 0 or not activos else rng.choice(activos).id,
                lineas=_lineas_oro(rng) if oro else _lineas(rng),
                oro_inversion=oro,
            ),
            actor=rng.choice(autores),
            origen=ORIGEN,
        )
    return cantidad


# Presupuestos de ejemplo (005, data-model «Datos de ejemplo»): por su posición en orden de fecha.
DIAS_PRESUPUESTOS_CADUCADOS: Final = (40, 150)  # más antiguos que la validez de 30 días
DIAS_PRESUPUESTOS_RECIENTES: Final = 25


async def _cargar_presupuestos(
    db: AsyncSession,
    rng: random.Random,
    resumen: ResumenCarga,
    *,
    cantidad: int,
    demo: list[Usuario],
    clientes: list[Cliente],
) -> None:
    """Unos 30 presupuestos de varios meses en todos los estados (FR-036).

    La mitad más antigua caduca y la reciente sigue pendiente, salvo los que se cierran: tres
    convertidos con su factura, dos en facturación con su borrador, dos sustituidos y dos anulados.
    Además, tres borradores de presupuesto, el primero sin cliente.
    """
    activos = [c for c in clientes if c.activo]
    facturables = [c for c in activos if c.direccion and c.localidad]
    if cantidad < 12 or not facturables:
        return
    admin = demo[0]
    validez = (await configuracion_repo.get(db)).validez_presupuesto_dias
    hoy_madrid = hoy()

    def clave() -> uuid.UUID:
        return uuid.UUID(int=rng.getrandbits(128), version=4)

    antiguos = cantidad // 2
    fechas = sorted(
        [
            hoy_madrid - timedelta(days=rng.randrange(*DIAS_PRESUPUESTOS_CADUCADOS))
            for _ in range(antiguos)
        ]
        + [
            hoy_madrid - timedelta(days=rng.randrange(0, DIAS_PRESUPUESTOS_RECIENTES))
            for _ in range(cantidad - antiguos)
        ]
    )
    # Los recientes que se cierran, siempre con un cliente facturable para poder convertir.
    recientes = list(range(antiguos, cantidad))
    convertidos, en_facturacion = recientes[0:6:2], recientes[6:10:2]
    sustituidos, anulados = recientes[1:5:2], [1, recientes[5]]
    oro = recientes[-1]
    emitidos: list[uuid.UUID] = []
    for indice, fecha in enumerate(fechas):
        se_convierte = indice in (*convertidos, *en_facturacion)
        presupuesto, _ = await presupuestos.emit_presupuesto(
            db,
            presupuestos.DatosPresupuesto(
                fecha=fecha,
                valido_hasta=fecha + timedelta(days=validez),
                cliente_id=rng.choice(facturables if se_convierte else activos).id,
                lineas=_lineas_oro(rng) if indice == oro else _lineas(rng),
                oro_inversion=indice == oro,
            ),
            actor=rng.choice(demo),
            origen=ORIGEN,
            clave=clave(),
        )
        emitidos.append(presupuesto.id)
    resumen.presupuestos = len(emitidos)

    for indice in (*convertidos, *en_facturacion):
        borrador, _ = await conversion.create_borrador_conversion(
            db, emitidos[indice], actor=rng.choice(demo), origen=ORIGEN
        )
        if indice not in convertidos:
            continue
        await borradores_srv.emit_borrador(
            db,
            borrador.id,
            borradores_srv.DatosBorrador(
                fecha_expedicion=hoy_madrid,
                cliente_id=borrador.cliente_id,
                lineas=tuple(
                    emision.DatosLinea(linea.unidades, linea.descripcion, linea.precio_unitario)
                    for linea in borrador.lineas
                ),
                oro_inversion=borrador.oro_inversion,
            ),
            version=borrador.version,
            actor=admin,
            origen=ORIGEN,
            clave=clave(),
        )
    for indice in sustituidos:
        original = await presupuestos_repo.get(db, emitidos[indice])
        if original is None:
            continue
        await presupuestos.modify_presupuesto(
            db,
            original.id,
            presupuestos.DatosPresupuesto(
                fecha=hoy_madrid,
                valido_hasta=hoy_madrid + timedelta(days=validez),
                cliente_id=original.cliente_id,
                lineas=_lineas(rng),
            ),
            motivo_texto=f"{MARCADOR} Cambio de pieza a petición del cliente.",
            actor=admin,
            origen=ORIGEN,
            clave=clave(),
        )
        resumen.presupuestos += 1
    for indice in anulados:
        await presupuestos.annul_presupuesto(
            db,
            emitidos[indice],
            motivo_texto=f"{MARCADOR} Rechazado por el cliente.",
            actor=admin,
            origen=ORIGEN,
            clave=clave(),
        )

    for indice in range(3):
        await borradores_presupuesto_srv.create_borrador(
            db,
            borradores_presupuesto_srv.DatosBorradorPresupuesto(
                fecha=hoy_madrid,
                valido_hasta=hoy_madrid + timedelta(days=validez),
                cliente_id=None if indice == 0 else rng.choice(activos).id,
                lineas=_lineas(rng),
            ),
            actor=rng.choice(demo),
            origen=ORIGEN,
        )
    resumen.borradores_presupuesto = 3


async def cargar(
    db: AsyncSession,
    *,
    clientes: int = 40,
    facturas: int = 50,
    borradores: int = 5,
    presupuestos: int = 30,
    contrasena_demo: str | None = None,
    semilla: int = 2026,
) -> ResumenCarga:
    if get_settings().es_produccion:
        msg = "La carga de datos de ejemplo no está permitida en producción."
        raise SinPermiso(msg)
    resumen = ResumenCarga()
    rng = random.Random(semilla)  # noqa: S311 — datos ficticios, no criptográficos
    if await usuarios_repo.get_by_nombre_usuario(db, "admin.demo") is not None:
        # Datos de 001 ya cargados: se añade solo la facturación, si aún no hay ninguna.
        if await registros_repo.exists_any(db) or await presupuestos_repo.exists_any(db):
            resumen.ya_cargados = True
            return resumen
        await _cargar_facturacion(
            db,
            rng,
            resumen,
            demo=await _usuarios_demo(db),
            clientes=await _clientes_de_ejemplo(db),
            facturas=facturas,
            borradores=borradores,
            presupuestos=presupuestos,
        )
        return resumen

    from faker import Faker

    fake = Faker("es_ES")
    fake.seed_instance(semilla)
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

    await _cargar_facturacion(
        db,
        rng,
        resumen,
        demo=demo,
        clientes=creados,
        facturas=facturas,
        borradores=borradores,
        presupuestos=presupuestos,
    )
    return resumen


async def _cargar_facturacion(
    db: AsyncSession,
    rng: random.Random,
    resumen: ResumenCarga,
    *,
    demo: list[Usuario],
    clientes: list[Cliente],
    facturas: int,
    borradores: int,
    presupuestos: int,
) -> None:
    """Configuración demo, facturas con correcciones y borradores (002, R-16), y presupuestos en
    todos sus estados (005, FR-036). Los presupuestos van después: sus conversiones son de hoy."""
    admin = demo[0]
    await _configurar_facturacion(db, admin)
    emitidas = await _emitir_facturas(db, rng, cantidad=facturas, emisores=demo, clientes=clientes)
    resumen.facturas_emitidas = len(emitidas)
    resumen.correcciones = await _corregir(db, rng, facturas=emitidas, admin=admin)
    resumen.borradores_creados = await _crear_borradores(
        db, rng, cantidad=borradores, autores=demo, clientes=clientes
    )
    await _cargar_presupuestos(
        db, rng, resumen, cantidad=presupuestos, demo=demo, clientes=clientes
    )


async def _usuarios_demo(db: AsyncSession) -> list[Usuario]:
    """Los usuarios de ejemplo que sigan activos, con el administrador primero."""
    demo: list[Usuario] = []
    for nombre_usuario, _, _ in USUARIOS_DEMO:
        usuario = await usuarios_repo.get_by_nombre_usuario(db, nombre_usuario)
        if usuario is not None and usuario.activo:
            demo.append(usuario)
    if not demo or demo[0].nombre_usuario != "admin.demo":
        msg = "El administrador de ejemplo (admin.demo) no está activo."
        raise SinPermiso(msg)
    return demo


async def _clientes_de_ejemplo(db: AsyncSession) -> list[Cliente]:
    resultado = await db.execute(
        select(Cliente)
        .where(Cliente.observaciones.startswith(MARCADOR))
        .order_by(Cliente.creado_en, Cliente.id)
    )
    return list(resultado.unique().scalars())
