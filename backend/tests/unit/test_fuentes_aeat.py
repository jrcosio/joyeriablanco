"""Las copias de los esquemas oficiales son las anotadas en research R-2 (004, constitución IV)."""

from hashlib import sha256
from pathlib import Path

import pytest

XSD = Path(__file__).resolve().parents[2] / "app" / "resources" / "aeat" / "xsd"


@pytest.mark.parametrize(
    ("fichero", "huella"),
    [
        (
            "SuministroInformacion.xsd",
            "ee4c1655175644de44c4c25055ffeb8e5f4bb4bc3834ce8254d4222ef18c8aa1",
        ),
        ("SuministroLR.xsd", "cbdac8d427cc5ab5d77ca48974cab0f35d6bb819c4c66db361681e3710aeba36"),
        ("EventosSIF.xsd", "cc7347c6a9a57a0c8edbc6b9ddcce55176452d0db0e68369477e207e9fbdd7e7"),
        (
            "xmldsig-core-schema.xsd",
            "d102ad3df7664c307e0c2c776ba4a90513b1969974d8a940bae1a77f9f21e15d",
        ),
    ],
)
def test_la_copia_es_la_oficial(fichero: str, huella: str) -> None:
    assert sha256((XSD / fichero).read_bytes()).hexdigest() == huella
