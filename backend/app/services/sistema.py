"""Datos del sistema informático y declaración responsable (004, US5; FR-027 a FR-029; R-13).

RRSIF, art. 13: la persona o entidad productora del sistema suscribe una declaración responsable,
visible en el propio sistema (13.2), y conserva las de todas sus versiones (13.3). Joyería Blanco
es productora y usuaria (uso propio, constitución 2.4.0).

Orden HAC/1177/2024, art. 15.1: empieza con el título literal y contiene, en este orden, las letras
a) a l), cada dato precedido del texto que lo describe. Los textos descriptivos siguen la redacción
de cada letra (F-10, BOE consolidado). Se puede descargar en PDF, un formato de uso extendido y
gratuito (art. 15.3).
"""

from dataclasses import dataclass
from datetime import date
from typing import Final

from app import __version__
from app.core.config import Settings, get_settings
from app.core.pdf import plantillas, render
from app.services.impresion_comun import DocumentoPdf

TITULO: Final = "DECLARACIÓN RESPONSABLE DEL SISTEMA INFORMÁTICO DE FACTURACIÓN"
MODALIDAD: Final = "no_verifactu"
COMPONENTES: Final = (
    "Servidor con la API de gestión (FastAPI) y la base de datos PostgreSQL, en contenedores "
    "Docker, y aplicación web de gestión que se usa desde el navegador. Gestiona clientes, "
    "presupuestos y facturas: emisión con numeración correlativa, rectificativas y anulaciones, "
    "registros de facturación y de evento encadenados y firmados, impresión en PDF con el código "
    "QR tributario, comprobación de la integridad y exportación de los registros."
)
FIRMA: Final = (
    "XAdES Enveloped (ETSI EN 319 132), clase EPES con la política de firma de la Administración "
    "General del Estado (urn:oid:2.16.724.1.3.1.1.2.1.9), RSA con SHA-256"
)
_MESES: Final = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


@dataclass(frozen=True, slots=True)
class Apartado:
    letra: str
    texto: str
    valor: str


@dataclass(frozen=True, slots=True)
class Declaracion:
    titulo: str
    sistema: str
    version: str
    productor: str
    apartados: tuple[Apartado, ...]


@dataclass(frozen=True, slots=True)
class Sistema:
    nombre: str
    id_sistema: str
    version: str
    numero_instalacion: str
    productor_nombre: str
    productor_nif: str
    productor_direccion: str
    modalidad: str
    declaracion: Declaracion


def _fecha(fecha: date | None) -> str:
    """Día, mes y año, en ese orden (art. 15.1.l)."""
    if fecha is None:
        return "Pendiente de suscribir (SIF_DECLARACION_FECHA)"
    return f"{fecha.day} de {_MESES[fecha.month - 1]} de {fecha.year}"


def _cumplimiento(productor: str, version: str) -> str:
    return (
        f"{productor} hace constar que el sistema informático, en la versión {version}, cumple con "
        "lo dispuesto en el artículo 29.2.j) de la Ley 58/2003, de 17 de diciembre, General "
        "Tributaria, en el Reglamento que establece los requisitos que deben adoptar los sistemas "
        "y programas informáticos o electrónicos que soporten los procesos de facturación de "
        "empresarios y profesionales, y la estandarización de formatos de los registros de "
        "facturación, aprobado por el Real Decreto 1007/2023, de 5 de diciembre, en la Orden "
        "HAC/1177/2024, de 17 de octubre, y en la sede electrónica de la Agencia Estatal de "
        "Administración Tributaria para todo aquello que complete las especificaciones de dicha "
        "orden."
    )


def declaration(ajustes: Settings | None = None) -> Declaracion:
    ajustes = ajustes or get_settings()
    productor = ajustes.sif_productor_nombre
    apartados = (
        Apartado("a", "Nombre del sistema informático", ajustes.sif_nombre_sistema),
        Apartado("b", "Código identificador del sistema informático", ajustes.sif_id_sistema),
        Apartado(
            "c",
            "Identificador completo de la versión concreta del sistema informático",
            __version__,
        ),
        Apartado(
            "d",
            "Componentes, hardware y software, de que consta el sistema informático, junto con "
            "una breve descripción de lo que hace y de sus principales funcionalidades",
            COMPONENTES,
        ),
        Apartado(
            "e",
            "Indicación de si el sistema informático se ha producido de tal manera que solo pueda "
            "funcionar exclusivamente como «VERI*FACTU»",
            "No",
        ),
        Apartado(
            "f",
            "Indicación de si el sistema informático permite ser usado por varios obligados "
            "tributarios o por un mismo usuario para dar soporte a la facturación de varios "
            "obligados tributarios",
            "No",
        ),
        Apartado(
            "g",
            "Tipos de firma utilizados para firmar los registros de facturación y de evento en el "
            "caso de que el sistema informático no sea utilizado como «VERI*FACTU»",
            FIRMA,
        ),
        Apartado(
            "h",
            "Nombre y apellidos o razón social de la persona o entidad productora del sistema "
            "informático",
            productor,
        ),
        Apartado(
            "i",
            "Número de identificación fiscal (NIF) español de la persona o entidad productora",
            ajustes.sif_productor_nif,
        ),
        Apartado(
            "j",
            "Dirección postal completa de contacto de la persona o entidad productora",
            ajustes.sif_productor_direccion,
        ),
        Apartado("k", "Declaración de cumplimiento", _cumplimiento(productor, __version__)),
        Apartado(
            "l",
            "Fecha y lugar en los que la persona o entidad productora suscribe la declaración "
            "responsable",
            f"{_fecha(ajustes.sif_declaracion_fecha)}, {ajustes.sif_declaracion_lugar}",
        ),
    )
    return Declaracion(
        titulo=TITULO,
        sistema=ajustes.sif_nombre_sistema,
        version=__version__,
        productor=productor,
        apartados=apartados,
    )


def system_info(ajustes: Settings | None = None) -> Sistema:
    ajustes = ajustes or get_settings()
    return Sistema(
        nombre=ajustes.sif_nombre_sistema,
        id_sistema=ajustes.sif_id_sistema,
        version=__version__,
        numero_instalacion=ajustes.sif_numero_instalacion,
        productor_nombre=ajustes.sif_productor_nombre,
        productor_nif=ajustes.sif_productor_nif,
        productor_direccion=ajustes.sif_productor_direccion,
        modalidad=MODALIDAD,
        declaracion=declaration(ajustes),
    )


async def declaration_pdf() -> DocumentoPdf:
    """La declaración en PDF «Paper» (art. 15.3), con el nombre de la versión."""
    html = plantillas.render_html("declaracion.html", {"d": declaration()})
    contenido = await render.en_hilo(lambda: render.html_a_pdf(html), render.LIMITE_FACTURAS)
    return DocumentoPdf(nombre=f"declaracion-responsable-{__version__}.pdf", contenido=contenido)
