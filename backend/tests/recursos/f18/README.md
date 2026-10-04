# Ejemplo oficial de registro firmado (F-18)

Ficheros del ZIP `AnexosEjemplosFirmaRegFact.zip` de la AEAT, que acompaña a la especificación de
la firma F-14 v0.1.5. Se copian sin ninguna modificación (004, research R-3).

- **URL**: `https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/Espec-Tecnicas/AnexosEjemplosFirmaRegFact.zip`
- **SHA-256 del ZIP**: `66fac533bef6c93c041b08704bf538843fe552052a2994899aba0875c2c4b24e`
- **Descarga**: 2026-10-03

| Fichero | SHA-256 |
|---|---|
| `ejemploRegistro.xml` | `328ff6571e8c75614f0fbe6e6456e472b897c2ed20a86ec42f2667782fdcdc8d` |
| `ejemploRegistro-firmado-epes-xades4j.xml` | `1aa6d87598e788cc1453e34865dada4eae427700099d3e84cb7029cc83f59666` |

`tests/integration/test_firma.py` firma `ejemploRegistro.xml` y compara su firma con la del
ejemplo firmado.
