"""Validación contra los XSD oficiales y firma XAdES-EPES de los registros (004, R-2 y R-3).

**Validación (R-2)**: con `lxml` y las copias locales de `app/resources/aeat/xsd/`. La importación
remota de `xmldsig-core-schema.xsd` se resuelve a la copia local: no hace falta red. Se valida el
registro ya firmado, que es lo que se guarda y se exporta, porque en `EventoType` la firma es
obligatoria. Un fallo es un error de programación y deshace la operación.

**Firma (R-3)**: F-14 v0.1.5, §4 a §6, reproduciendo nodo a nodo el ejemplo oficial F-18
(`ejemploRegistro-firmado-epes-xades4j.xml`):
- XAdES 1.3.2 «Enveloped» sobre el elemento raíz (`RegistroAlta`, `RegistroAnulacion` o
  `RegistroEvento`), con la firma en su `Signature`: al final del registro o, en el evento, al final
  de `Evento`.
- C14N inclusiva 20010315, `rsa-sha256` y digest SHA-256. La referencia a los datos es `URI=""` con
  la única transformación *enveloped*, y la otra referencia va a `SignedProperties`.
- `SigningTime` en hora de Madrid. `SigningCertificate` con la cadena del PKCS#12 (SHA-1 e
  `IssuerSerial`), la forma del ejemplo. signxml no admite a la vez `SigningCertificateV2`.
- `SignaturePolicyIdentifier` con la política de la AGE: OID, hash SHA-1 y `SPURI`.
- `DataObjectFormat` con `ObjectIdentifier`, `MimeType` `text/xml` y `Encoding` `UTF-8`.
- `KeyInfo` con `X509Data` y `KeyValue`.

La subclase de `XAdESSigner` sobrescribe métodos de signxml 5.1, por eso la dependencia se fija en
`>=5.1,<5.2`.
"""

import logging
import secrets
from base64 import b64encode
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from functools import lru_cache
from hashlib import sha1, sha256
from pathlib import Path
from typing import Any, Final

from cryptography import exceptions as criptografia
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
from lxml import etree
from signxml.algorithms import CanonicalizationMethod, DigestAlgorithm
from signxml.exceptions import SignXMLException
from signxml.xades.xades import (
    XAdESDataObjectFormat,
    XAdESSignatureConfiguration,
    XAdESSignaturePolicy,
    XAdESSigner,
    XAdESVerifier,
)

from app.domain.huella import ZONA_REGISTRO
from app.domain.xml_registro import NS_DS
from app.services.certificado import CertificadoFirma

logger = logging.getLogger(__name__)
# signxml escribe en DEBUG el XML canonicalizado, con datos personales e importes. Nunca debe
# llegar a los registros de actividad, sea cual sea el nivel configurado (004, FR-033).
logging.getLogger("signxml").setLevel(logging.WARNING)

XSD_DIR: Final = Path(__file__).resolve().parents[1] / "resources" / "aeat" / "xsd"
_URL_XMLDSIG: Final = "http://www.w3.org/TR/xmldsig-core/xmldsig-core-schema.xsd"

# F-14 §4: política de firma de la AGE (anexo 1), con el hash SHA-1 que publica la propia F-14.
POLITICA: Final = XAdESSignaturePolicy(
    Identifier="urn:oid:2.16.724.1.3.1.1.2.1.9",
    Description="",
    DigestMethod=DigestAlgorithm.SHA1,
    DigestValue="G7roucf600+f03r/o0bAOQ6WAs0=",
)
SPURI: Final = "https://sede.administracion.gob.es/politica_de_firma_anexo_1.pdf"
OID_XML: Final = "urn:oid:1.2.840.10003.5.109.10"  # ObjectIdentifier del ejemplo F-18
C14N_INCLUSIVA: Final = CanonicalizationMethod.CANONICAL_XML_1_0
NS_XADES: Final = "http://uri.etsi.org/01903/v1.3.2#"
_NSMAP: Final = {"ds": NS_DS, "xades": NS_XADES}


class Esquema(StrEnum):
    SUMINISTRO = "SuministroInformacion.xsd"
    EVENTOS = "EventosSIF.xsd"


class XmlNoValido(Exception):
    """El XML no cumple el esquema oficial."""


class FirmaNoValida(Exception):
    """La firma no se verifica (anomalía 02)."""


class _ResolvedorLocal(etree.Resolver):
    def resolve(self, system_url: str | None, public_id: str | None, context: Any) -> Any:
        if system_url == _URL_XMLDSIG:
            return self.resolve_filename(str(XSD_DIR / "xmldsig-core-schema.xsd"), context)
        return None


def _parser() -> etree.XMLParser:
    parser = etree.XMLParser(no_network=True, resolve_entities=False, load_dtd=False)
    parser.resolvers.add(_ResolvedorLocal())
    return parser


@lru_cache
def _esquema(esquema: Esquema) -> etree.XMLSchema:
    return etree.XMLSchema(etree.parse(str(XSD_DIR / esquema.value), _parser()))


def validar(elemento: etree._Element, esquema: Esquema) -> None:
    """Valida contra el XSD oficial (R-2). `XmlNoValido` con el primer error si no lo cumple."""
    compilado = _esquema(esquema)
    if not compilado.validate(elemento):
        error = compilado.error_log.last_error
        msg = f"El registro no cumple {esquema.value}: {error.message if error else '¿?'}"
        raise XmlNoValido(msg)


def _x(nombre: str) -> str:
    return f"{{{NS_XADES}}}{nombre}"


def _pem(base64: str) -> bytes:
    """Certificado de `X509Certificate` (base64 de su DER) en PEM."""
    cuerpo = "".join(base64.split())
    return f"-----BEGIN CERTIFICATE-----\n{cuerpo}\n-----END CERTIFICATE-----\n".encode("ascii")


def _sub(padre: etree._Element, etiqueta: str, texto: str | None = None, **atributos: str) -> Any:
    hijo = etree.SubElement(padre, etiqueta, attrib=atributos, nsmap=_NSMAP)
    if texto is not None:
        hijo.text = texto
    return hijo


class _FirmanteAeat(XAdESSigner):
    """`XAdESSigner` ajustado al ejemplo oficial F-18 (ver el docstring del módulo)."""

    def __init__(self, momento: datetime) -> None:
        super().__init__(
            signature_policy=POLITICA,
            claimed_roles=None,
            data_object_format=XAdESDataObjectFormat(Description="", MimeType="text/xml"),
            c14n_algorithm=C14N_INCLUSIVA,
        )
        self._momento = momento

    def _build_xades_ds_object(self, sig_root: Any, signing_settings: Any) -> None:
        """Como en signxml 5.1, pero sin la referencia al `KeyInfo`: F-18 solo firma los datos y
        las `SignedProperties`."""
        ds_object = _sub(sig_root, f"{{{NS_DS}}}Object")
        if "Id" not in sig_root.attrib:
            sig_root.set("Id", f"Signature-{secrets.token_hex(8).upper()}")
        propiedades = _sub(ds_object, _x("QualifyingProperties"), Target=f"#{sig_root.get('Id')}")
        firmadas = _sub(
            propiedades,
            _x("SignedProperties"),
            Id=f"{sig_root.get('Id')}-SignedProperties",
        )
        de_firma = _sub(firmadas, _x("SignedSignatureProperties"))
        for anotador in self.signed_signature_properties_annotators:
            anotador(de_firma, sig_root=sig_root, signing_settings=signing_settings)
        de_datos = _sub(firmadas, _x("SignedDataObjectProperties"))
        for anotador_datos in self.signed_data_object_properties_annotators:
            anotador_datos(de_datos, sig_root=sig_root, signing_settings=signing_settings)
        # Referencia a las `SignedProperties` como en F-18: con la transformación C14N explícita.
        signxml: Any = self  # métodos internos de signxml 5.1, sin anotaciones de tipos
        referencia = _sub(
            sig_root.find(f"{{{NS_DS}}}SignedInfo"),
            f"{{{NS_DS}}}Reference",
            URI=f"#{firmadas.get('Id')}",
            Type="http://uri.etsi.org/01903#SignedProperties",
        )
        transformaciones = _sub(referencia, f"{{{NS_DS}}}Transforms")
        _sub(transformaciones, f"{{{NS_DS}}}Transform", Algorithm=C14N_INCLUSIVA.value)
        _sub(referencia, f"{{{NS_DS}}}DigestMethod", Algorithm=self.digest_alg.value)
        canonica = signxml._c14n(firmadas, algorithm=self.c14n_alg)
        _sub(referencia, f"{{{NS_DS}}}DigestValue", b64encode(sha256(canonica).digest()).decode())

    def add_signing_time(
        self, signed_signature_properties: Any, sig_root: Any, signing_settings: Any
    ) -> None:
        momento = self._momento.astimezone(ZONA_REGISTRO).isoformat(timespec="seconds")
        _sub(signed_signature_properties, _x("SigningTime"), momento)

    def add_signing_certificate(
        self, signed_signature_properties: Any, sig_root: Any, signing_settings: Any
    ) -> None:
        firmante = _sub(signed_signature_properties, _x("SigningCertificate"))
        for pem in signing_settings.cert_chain:
            cert = x509.load_pem_x509_certificate(
                pem.encode("ascii") if isinstance(pem, str) else pem
            )
            nodo = _sub(firmante, _x("Cert"))
            resumen = _sub(nodo, _x("CertDigest"))
            _sub(resumen, f"{{{NS_DS}}}DigestMethod", Algorithm=DigestAlgorithm.SHA1.value)
            huella = sha1(cert.public_bytes(Encoding.DER)).digest()  # noqa: S324 — XAdES/F-18
            _sub(resumen, f"{{{NS_DS}}}DigestValue", b64encode(huella).decode())
            emisor = _sub(nodo, _x("IssuerSerial"))
            _sub(emisor, f"{{{NS_DS}}}X509IssuerName", cert.issuer.rfc4514_string())
            _sub(emisor, f"{{{NS_DS}}}X509SerialNumber", str(cert.serial_number))

    def add_signature_policy_identifier(
        self, signed_signature_properties: Any, sig_root: Any, signing_settings: Any
    ) -> None:
        super().add_signature_policy_identifier(
            signed_signature_properties, sig_root=sig_root, signing_settings=signing_settings
        )
        politica = signed_signature_properties.find(
            f"{{{NS_XADES}}}SignaturePolicyIdentifier/{{{NS_XADES}}}SignaturePolicyId"
        )
        calificadores = _sub(politica, _x("SigPolicyQualifiers"))
        _sub(_sub(calificadores, _x("SigPolicyQualifier")), _x("SPURI"), SPURI)

    def add_data_object_format(
        self, signed_data_object_properties: Any, sig_root: Any, signing_settings: Any
    ) -> None:
        referencia = sig_root.find(f"{{{NS_DS}}}SignedInfo/{{{NS_DS}}}Reference")
        if "Id" not in referencia.attrib:
            referencia.set("Id", f"{sig_root.get('Id')}-ref0")
        formato = _sub(
            signed_data_object_properties,
            _x("DataObjectFormat"),
            ObjectReference=f"#{referencia.get('Id')}",
        )
        identificador = _sub(formato, _x("ObjectIdentifier"))
        _sub(identificador, _x("Identifier"), OID_XML)
        _sub(identificador, _x("Description"), "")
        _sub(formato, _x("MimeType"), "text/xml")
        _sub(formato, _x("Encoding"), "UTF-8")


def firmar(elemento: etree._Element, certificado: CertificadoFirma, momento: datetime) -> bytes:
    """Firma el registro y devuelve el XML UTF-8 tal como se guarda y se exporta."""
    cadena = [c.public_bytes(Encoding.PEM).decode("ascii") for c in certificado.cadena]
    firmado = _FirmanteAeat(momento).sign(
        elemento,
        key=certificado.clave,
        cert=cadena,
        always_add_key_value=True,
        exclude_c14n_transform_element=True,
    )
    return bytes(etree.tostring(firmado, encoding="UTF-8", xml_declaration=True))


def sign_and_validate(
    elemento: etree._Element, esquema: Esquema, certificado: CertificadoFirma, momento: datetime
) -> bytes:
    """Firma el registro y valida el resultado contra su XSD: lo que se guarda y se exporta."""
    xml = firmar(elemento, certificado, momento)
    validar(etree.fromstring(xml), esquema)
    return xml


@dataclass(frozen=True, slots=True)
class FirmaVerificada:
    certificado: x509.Certificate

    @property
    def huella(self) -> str:
        return sha256(self.certificado.public_bytes(Encoding.DER)).hexdigest().upper()


def verificar(xml: bytes, *, en: datetime) -> FirmaVerificada:
    """Verifica la firma con el certificado que lleva (anomalía 02 si no).

    La vigencia del certificado se comprueba en `en`, la fecha y hora de generación del registro
    (F-14 §3): un registro firmado con un certificado que caducó después sigue siendo válido. No
    se valida la cadena de confianza: quien comprueba la integridad coteja además la huella del
    certificado guardada (R-9).
    """
    try:
        raiz = etree.fromstring(xml, parser=_parser())
        nodo = raiz.find(f".//{{{NS_DS}}}KeyInfo/{{{NS_DS}}}X509Data/{{{NS_DS}}}X509Certificate")
        if nodo is None or not nodo.text:
            msg = "La firma no lleva el certificado"
            raise FirmaNoValida(msg)
        certificado = x509.load_pem_x509_certificate(_pem(nodo.text))
        XAdESVerifier().verify(
            xml,
            x509_cert=certificado,
            expect_signature_policy=POLITICA,
            expect_config=XAdESSignatureConfiguration(expect_references=2, verification_time=en),
        )
    except FirmaNoValida:
        raise
    except (
        SignXMLException,
        criptografia.InvalidSignature,
        ValueError,
        etree.XMLSyntaxError,
    ) as exc:
        raise FirmaNoValida(str(exc)) from exc
    return FirmaVerificada(certificado=certificado)
