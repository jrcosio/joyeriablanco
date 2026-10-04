"""⚖️ Test obligatorio (constitución VII, 2.4.0): firma XAdES-EPES de los registros (004, R-3).

La firma reproduce el ejemplo oficial F-18 (`tests/recursos/f18/`) con los elementos que exige
F-14 v0.1.5, §4 a §6. Firmando el mismo `ejemploRegistro.xml`, la referencia a los datos da el
mismo `DigestValue` que el ejemplo de la AEAT, así que la canonicalización coincide byte a byte.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from lxml import etree

from app.domain.xml_registro import NS_DS, NS_SUMINISTRO, canonical, without_signature
from app.services import firma
from app.services.certificado import CertificadoFirma
from tests.certificados import certificado_firma

F18 = Path(__file__).resolve().parents[1] / "recursos" / "f18"
NS = {"ds": NS_DS, "xades": firma.NS_XADES}
AHORA = datetime.now(UTC)


@pytest.fixture(scope="module")
def firmante() -> CertificadoFirma:
    return certificado_firma()


@pytest.fixture(scope="module")
def firmado(firmante: CertificadoFirma) -> bytes:
    return firma.firmar(etree.parse(F18 / "ejemploRegistro.xml").getroot(), firmante, AHORA)


def _uno(raiz: etree._Element, ruta: str) -> etree._Element:
    [nodo] = raiz.xpath(ruta, namespaces=NS)
    assert isinstance(nodo, etree._Element)
    return nodo


def test_la_firma_se_verifica_con_su_certificado(
    firmado: bytes, firmante: CertificadoFirma
) -> None:
    verificada = firma.verificar(firmado, en=AHORA)

    assert verificada.huella == firmante.huella


def test_el_registro_firmado_sigue_cumpliendo_el_esquema(firmado: bytes) -> None:
    firma.validar(etree.fromstring(firmado), firma.Esquema.SUMINISTRO)


def test_la_firma_va_en_el_nodo_firmado_y_al_final(firmado: bytes) -> None:
    raiz = etree.fromstring(firmado)

    assert raiz.tag == f"{{{NS_SUMINISTRO}}}RegistroAlta"
    assert raiz[-1].tag == f"{{{NS_DS}}}Signature"
    assert len(raiz.findall(f".//{{{NS_DS}}}Signature")) == 1


def test_lleva_los_elementos_del_ejemplo_oficial(firmado: bytes) -> None:
    raiz = etree.fromstring(firmado)
    info = "ds:Signature/ds:SignedInfo"

    assert _uno(raiz, f"{info}/ds:CanonicalizationMethod").get("Algorithm") == (
        "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
    )
    assert _uno(raiz, f"{info}/ds:SignatureMethod").get("Algorithm") == (
        "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
    )
    datos = _uno(raiz, f"{info}/ds:Reference[@URI='']")
    assert [t.get("Algorithm") for t in datos.findall("ds:Transforms/ds:Transform", NS)] == [
        "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
    ]
    assert _uno(datos, "ds:DigestMethod").get("Algorithm") == (
        "http://www.w3.org/2001/04/xmlenc#sha256"
    )
    assert len(raiz.xpath(f"{info}/ds:Reference", namespaces=NS)) == 2

    propiedades = "ds:Signature/ds:Object/xades:QualifyingProperties/xades:SignedProperties"
    firmadas = f"{propiedades}/xades:SignedSignatureProperties"
    assert _uno(raiz, f"{firmadas}/xades:SigningTime").text
    assert (
        _uno(raiz, f"{firmadas}/xades:SigningCertificate/xades:Cert/xades:IssuerSerial") is not None
    )
    assert not raiz.xpath(f"{firmadas}/xades:SigningCertificateV2", namespaces=NS)
    politica = f"{firmadas}/xades:SignaturePolicyIdentifier/xades:SignaturePolicyId"
    assert _uno(raiz, f"{politica}/xades:SigPolicyId/xades:Identifier").text == (
        "urn:oid:2.16.724.1.3.1.1.2.1.9"
    )
    assert _uno(raiz, f"{politica}/xades:SigPolicyHash/ds:DigestValue").text == (
        "G7roucf600+f03r/o0bAOQ6WAs0="
    )
    assert _uno(raiz, f"{politica}//xades:SPURI").text == (
        "https://sede.administracion.gob.es/politica_de_firma_anexo_1.pdf"
    )
    formato = f"{propiedades}/xades:SignedDataObjectProperties/xades:DataObjectFormat"
    assert _uno(raiz, f"{formato}/xades:MimeType").text == "text/xml"
    assert _uno(raiz, f"{formato}/xades:Encoding").text == "UTF-8"
    assert _uno(raiz, "ds:Signature/ds:KeyInfo/ds:X509Data/ds:X509Certificate").text
    assert _uno(raiz, "ds:Signature/ds:KeyInfo/ds:KeyValue/ds:RSAKeyValue") is not None


def test_la_canonicalizacion_coincide_con_la_del_ejemplo_de_la_aeat(firmado: bytes) -> None:
    oficial = etree.parse(F18 / "ejemploRegistro-firmado-epes-xades4j.xml").getroot()
    nuestra = etree.fromstring(firmado)
    ruta = "ds:Signature/ds:SignedInfo/ds:Reference[@URI='']/ds:DigestValue"

    assert _uno(nuestra, ruta).text == _uno(oficial, ruta).text


def test_alterar_un_caracter_rompe_la_firma(firmado: bytes) -> None:
    alterado = firmado.replace(b"<sum1:ImporteTotal>241.4", b"<sum1:ImporteTotal>241.5")
    assert alterado != firmado

    with pytest.raises(firma.FirmaNoValida):
        firma.verificar(alterado, en=AHORA)


def test_alterar_la_firma_rompe_la_firma(firmado: bytes) -> None:
    raiz = etree.fromstring(firmado)
    valor = _uno(raiz, "ds:Signature/ds:SignatureValue")
    valor.text = "A" + (valor.text or "")[1:]

    with pytest.raises(firma.FirmaNoValida):
        firma.verificar(etree.tostring(raiz), en=AHORA)


def test_se_verifica_en_la_fecha_del_registro_aunque_el_certificado_caduque_despues() -> None:
    corto = certificado_firma(desde=AHORA - timedelta(days=1), dias=2)
    xml = firma.firmar(etree.parse(F18 / "ejemploRegistro.xml").getroot(), corto, AHORA)

    assert firma.verificar(xml, en=AHORA)
    with pytest.raises(firma.FirmaNoValida):
        firma.verificar(xml, en=AHORA + timedelta(days=30))


def test_sin_la_firma_queda_el_registro_original(firmado: bytes) -> None:
    original = etree.parse(F18 / "ejemploRegistro.xml").getroot()

    assert canonical(without_signature(firmado)) == canonical(original)


def test_un_xml_que_no_cumple_el_esquema_se_rechaza() -> None:
    raiz = etree.parse(F18 / "ejemploRegistro.xml").getroot()
    raiz.remove(raiz[0])  # sin IDVersion

    with pytest.raises(firma.XmlNoValido, match="SuministroInformacion"):
        firma.validar(raiz, firma.Esquema.SUMINISTRO)
