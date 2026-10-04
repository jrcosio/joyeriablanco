# Esquemas XSD oficiales (004, research R-2)

Copias literales, sin ninguna modificación, de los esquemas con que se generan y se validan los
registros de facturación y de evento de la modalidad No VERI\*FACTU. Se descargaron el 2026-10-03.
`tests/unit/test_fuentes_aeat.py` comprueba que los SHA-256 siguen siendo estos.

| Fichero | Fuente | URL | SHA-256 |
|---|---|---|---|
| `SuministroInformacion.xsd` | F-15 (AEAT, IDVersion 1.0) | `https://prewww2.aeat.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/SuministroInformacion.xsd` | `ee4c1655175644de44c4c25055ffeb8e5f4bb4bc3834ce8254d4222ef18c8aa1` |
| `SuministroLR.xsd` | F-16 (AEAT, 1.0) | `https://prewww2.aeat.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/SuministroLR.xsd` | `cbdac8d427cc5ab5d77ca48974cab0f35d6bb819c4c66db361681e3710aeba36` |
| `EventosSIF.xsd` | F-17 (AEAT, IDVersion 1.0) | `https://prewww2.aeat.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/EventosSIF.xsd` | `cc7347c6a9a57a0c8edbc6b9ddcce55176452d0db0e68369477e207e9fbdd7e7` |
| `xmldsig-core-schema.xsd` | F-20 (W3C, REC 2002) | `http://www.w3.org/TR/xmldsig-core/xmldsig-core-schema.xsd` | `d102ad3df7664c307e0c2c776ba4a90513b1969974d8a940bae1a77f9f21e15d` |

F-15 y F-17 importan el esquema de XML-DSig por su URL del W3C. `services/firma.py` la resuelve a la
copia local, así que la validación no necesita red.
