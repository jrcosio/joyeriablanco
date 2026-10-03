"""Certificado de firma de los registros (004, research R-6; F-14 §3; Orden, art. 14).

Lo instala quien despliega: un PKCS#12 en `CERTIFICADO_RUTA` con su contraseña en
`CERTIFICADO_CONTRASENA`. Nunca se guarda en la BD, y ni la contraseña ni la clave privada salen de
este módulo: la API solo ve el `EstadoCertificado`, y los registros de actividad, el motivo.

- Se carga una vez por proceso y se recarga si cambia el fichero (fecha de modificación y tamaño).
- La validez se comprueba en la fecha y hora de generación del registro, no en la de hoy (F-14 §3).
- Un certificado autofirmado o marcado `O=PRUEBAS - SIN VALIDEZ` (el de `generar-certificado-
  pruebas`) solo vale fuera de producción.
- Lo que no se comprueba: la lista de confianza de la UE y la revocación en línea (spec,
  «Assumptions»).
"""

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Final

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, Encoding, pkcs12
from cryptography.x509.oid import ExtensionOID, NameOID

from app.core.config import Settings, get_settings
from app.core.tiempo import ahora

logger = logging.getLogger(__name__)

AVISO_CADUCIDAD: Final = timedelta(days=30)  # FR-003
MARCA_PRUEBAS: Final = "PRUEBAS - SIN VALIDEZ"
_PREFIJOS_IDENTIFICACION: Final = re.compile(r"^(IDC[A-Z]{2}|VAT[A-Z]{2})-")


class MotivoNoUtilizable(StrEnum):
    NO_INSTALADO = "no_instalado"
    ILEGIBLE = "ilegible"
    CADUCADO = "caducado"
    AUN_NO_VALIDO = "aun_no_valido"
    SIN_CLAVE_PRIVADA = "sin_clave_privada"
    NO_APTO_PARA_FIRMAR = "no_apto_para_firmar"
    DE_PRUEBAS_EN_PRODUCCION = "de_pruebas_en_produccion"


TEXTO_MOTIVO: Final[dict[MotivoNoUtilizable, str]] = {
    MotivoNoUtilizable.NO_INSTALADO: "no hay ningún certificado instalado",
    MotivoNoUtilizable.ILEGIBLE: "no se puede leer el certificado o su contraseña no es correcta",
    MotivoNoUtilizable.CADUCADO: "el certificado ha caducado",
    MotivoNoUtilizable.AUN_NO_VALIDO: "el certificado todavía no es válido",
    MotivoNoUtilizable.SIN_CLAVE_PRIVADA: "el fichero no contiene la clave privada",
    MotivoNoUtilizable.NO_APTO_PARA_FIRMAR: "el certificado no permite firmar con RSA",
    MotivoNoUtilizable.DE_PRUEBAS_EN_PRODUCCION: "es un certificado de pruebas",
}


class CertificadoNoUtilizable(Exception):
    def __init__(self, motivo: MotivoNoUtilizable) -> None:
        self.motivo = motivo
        super().__init__(TEXTO_MOTIVO[motivo])


def _atributo(nombre: x509.Name, oid: x509.ObjectIdentifier) -> str | None:
    valores = nombre.get_attributes_for_oid(oid)
    return str(valores[0].value) if valores else None


@dataclass(frozen=True, slots=True)
class CertificadoFirma:
    """El certificado con su clave, ya comprobado que sirve para firmar con RSA."""

    clave: rsa.RSAPrivateKey
    certificado: x509.Certificate
    adicionales: tuple[x509.Certificate, ...]

    @property
    def cadena(self) -> tuple[x509.Certificate, ...]:
        return (self.certificado, *self.adicionales)

    @property
    def titular(self) -> str:
        nombre = _atributo(self.certificado.subject, NameOID.COMMON_NAME)
        return (nombre or self.certificado.subject.rfc4514_string())[:200]

    @property
    def identificacion(self) -> str | None:
        """El NIF del sujeto: `organizationIdentifier` (VATES-…) o `serialNumber` (IDCES-…)."""
        sujeto = self.certificado.subject
        valor = _atributo(sujeto, NameOID.ORGANIZATION_IDENTIFIER) or _atributo(
            sujeto, NameOID.SERIAL_NUMBER
        )
        return _PREFIJOS_IDENTIFICACION.sub("", valor) if valor else None

    @property
    def emisor(self) -> str:
        nombre = _atributo(self.certificado.issuer, NameOID.COMMON_NAME)
        return nombre or self.certificado.issuer.rfc4514_string()

    @property
    def huella(self) -> str:
        """SHA-256 del certificado (DER) en hexadecimal mayúsculas: `certificado_huella`."""
        return sha256(self.certificado.public_bytes(Encoding.DER)).hexdigest().upper()

    @property
    def de_pruebas(self) -> bool:
        cert = self.certificado
        marca = _atributo(cert.subject, NameOID.ORGANIZATION_NAME) == MARCA_PRUEBAS
        return marca or cert.issuer == cert.subject


@dataclass(frozen=True, slots=True)
class EstadoCertificado:
    motivo: MotivoNoUtilizable | None
    titular: str | None = None
    identificacion: str | None = None
    emisor: str | None = None
    valido_desde: datetime | None = None
    valido_hasta: datetime | None = None
    dias_restantes: int | None = None
    caduca_pronto: bool = False

    @property
    def utilizable(self) -> bool:
        return self.motivo is None


type _Cargado = CertificadoFirma | MotivoNoUtilizable

_cache: dict[tuple[str, int, int, str], _Cargado] = {}


def _leer(ruta: Path, contrasena: bytes) -> _Cargado:
    try:
        clave, certificado, adicionales = pkcs12.load_key_and_certificates(
            ruta.read_bytes(), contrasena
        )
    except (OSError, ValueError):
        return MotivoNoUtilizable.ILEGIBLE
    if clave is None:
        # Sin clave, el certificado llega entre los «adicionales»: no hay nada con qué firmar.
        hay_certificados = certificado is not None or bool(adicionales)
        return (
            MotivoNoUtilizable.SIN_CLAVE_PRIVADA
            if hay_certificados
            else MotivoNoUtilizable.ILEGIBLE
        )
    if certificado is None:
        return MotivoNoUtilizable.ILEGIBLE
    if not isinstance(clave, rsa.RSAPrivateKey) or clave.key_size < 1024:  # F-14 §4
        return MotivoNoUtilizable.NO_APTO_PARA_FIRMAR
    try:
        uso = certificado.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE).value
    except x509.ExtensionNotFound:
        uso = None
    if isinstance(uso, x509.KeyUsage) and not (uso.digital_signature or uso.content_commitment):
        return MotivoNoUtilizable.NO_APTO_PARA_FIRMAR
    return CertificadoFirma(clave=clave, certificado=certificado, adicionales=tuple(adicionales))


def _cargar(ajustes: Settings) -> _Cargado:
    ruta, contrasena = ajustes.certificado_ruta, ajustes.certificado_contrasena
    if ruta is None or contrasena is None:
        return MotivoNoUtilizable.NO_INSTALADO
    try:
        info = ruta.stat()
    except OSError:
        return MotivoNoUtilizable.NO_INSTALADO
    secreto = contrasena.get_secret_value().encode("utf-8")
    # La contraseña entra en la clave de la caché solo como huella: cambiarla obliga a releer.
    clave_cache = (str(ruta), info.st_mtime_ns, info.st_size, sha256(secreto).hexdigest())
    if (cargado := _cache.get(clave_cache)) is None:
        _cache.clear()
        cargado = _leer(ruta, secreto)
        _cache[clave_cache] = cargado
        if isinstance(cargado, MotivoNoUtilizable):
            logger.warning("Certificado de firma no utilizable", extra={"motivo": cargado.value})
        else:
            logger.info("Certificado de firma cargado", extra={"huella": cargado.huella[:12]})
    return cargado


def _motivo_en(
    firma: CertificadoFirma, momento: datetime, ajustes: Settings
) -> MotivoNoUtilizable | None:
    cert = firma.certificado
    if momento < cert.not_valid_before_utc:
        return MotivoNoUtilizable.AUN_NO_VALIDO
    if momento > cert.not_valid_after_utc:
        return MotivoNoUtilizable.CADUCADO
    if ajustes.es_produccion and firma.de_pruebas:
        return MotivoNoUtilizable.DE_PRUEBAS_EN_PRODUCCION
    return None


def utilizable(en: datetime | None = None, *, ajustes: Settings | None = None) -> CertificadoFirma:
    """El certificado con que firmar un registro generado en `en`, o `CertificadoNoUtilizable`."""
    ajustes = ajustes or get_settings()
    cargado = _cargar(ajustes)
    if isinstance(cargado, MotivoNoUtilizable):
        raise CertificadoNoUtilizable(cargado)
    if motivo := _motivo_en(cargado, en or ahora(), ajustes):
        raise CertificadoNoUtilizable(motivo)
    return cargado


def estado(en: datetime | None = None, *, ajustes: Settings | None = None) -> EstadoCertificado:
    """Lo que se puede mostrar del certificado (FR-003): nunca la clave ni la contraseña."""
    ajustes = ajustes or get_settings()
    momento = en or ahora()
    cargado = _cargar(ajustes)
    if isinstance(cargado, MotivoNoUtilizable):
        return EstadoCertificado(motivo=cargado)
    hasta = cargado.certificado.not_valid_after_utc
    restante = hasta - momento
    return EstadoCertificado(
        motivo=_motivo_en(cargado, momento, ajustes),
        titular=cargado.titular,
        identificacion=cargado.identificacion,
        emisor=cargado.emisor,
        valido_desde=cargado.certificado.not_valid_before_utc,
        valido_hasta=hasta,
        dias_restantes=max(restante.days, 0),
        caduca_pronto=timedelta(0) <= restante <= AVISO_CADUCIDAD,
    )


def generar_pkcs12(
    contrasena: str,
    *,
    titular: str = "JOYERIA BLANCO (PRUEBAS)",
    nif: str = "B12345674",
    desde: datetime | None = None,
    dias: int = 365,
    firma: bool = True,
    con_clave: bool = True,
    marca_pruebas: bool = True,
) -> bytes:
    """Un PKCS#12 autofirmado para desarrollo, E2E y tests (R-6). En producción no es utilizable.

    `firma=False` quita el uso de firma del `KeyUsage`, `con_clave=False` deja el fichero sin la
    clave privada y `marca_pruebas=False` omite `O=PRUEBAS - SIN VALIDEZ`: sirven para los tests
    de cada motivo de no utilizable.
    """
    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    atributos = [
        x509.NameAttribute(NameOID.COUNTRY_NAME, "ES"),
        x509.NameAttribute(NameOID.SERIAL_NUMBER, f"IDCES-{nif}"),
        x509.NameAttribute(NameOID.COMMON_NAME, titular),
    ]
    if marca_pruebas:
        atributos.insert(1, x509.NameAttribute(NameOID.ORGANIZATION_NAME, MARCA_PRUEBAS))
    nombre = x509.Name(atributos)
    inicio = desde or (datetime.now(UTC) - timedelta(days=1))
    certificado = (
        x509.CertificateBuilder()
        .subject_name(nombre)
        .issuer_name(nombre)
        .public_key(clave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(inicio)
        .not_valid_after(inicio + timedelta(days=dias))
        .add_extension(
            x509.KeyUsage(
                digital_signature=firma,
                content_commitment=firma,
                key_encipherment=not firma,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(clave, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        b"certificado-pruebas",
        clave if con_clave else None,
        certificado,
        None,
        BestAvailableEncryption(contrasena.encode("utf-8")),
    )
