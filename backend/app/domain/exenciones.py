"""Exención de la venta de oro de inversión (ajuste de cierre de 002; FR-052, research R-21).

- F-11: Ley 37/1992 (LIVA), título IX, capítulo V, «Régimen especial del oro de inversión».
  Art. 140 bis.Uno.1.º: «Estarán exentas del impuesto […] Las entregas, adquisiciones
  intracomunitarias e importaciones de oro de inversión».
- F-1: DsRegistroVeriFactu.xlsx v1.0, hoja «6) Listas». L8A «04 Régimen especial del oro de
  inversión.» y L10 «E6 Exenta por otros» (E1–E5 son los arts. 20 a 25 de la LIVA).
- F-3 §15.6.3: «si clave de ClaveRegimen es igual a "04", CalificacionOperacion solo puede ser
  "S2", o bien OperacionExenta».
- F-6 (ROF), art. 6.1.j: la factura exenta lleva «una referencia a […] los preceptos
  correspondientes de la Ley del Impuesto».

La asesoría confirma esta codificación antes de producción (research R-17, Q-10).
"""

from typing import Final

CLAVE_REGIMEN_ORO_INVERSION: Final = "04"  # L8A
OPERACION_EXENTA_OTROS: Final = "E6"  # L10
MENCION_EXENCION_ORO_INVERSION: Final = (
    "Operación exenta de IVA (art. 140 bis.Uno.1.º de la Ley 37/1992)"
)


def is_oro_inversion(clave_regimen: str) -> bool:
    return clave_regimen == CLAVE_REGIMEN_ORO_INVERSION


def mencion_exencion(clave_regimen: str) -> str | None:
    """Mención que exige el ROF, art. 6.1.j, en la factura con esa clave (o `None`)."""
    return MENCION_EXENCION_ORO_INVERSION if is_oro_inversion(clave_regimen) else None
