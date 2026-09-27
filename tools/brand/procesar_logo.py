# /// script
# requires-python = ">=3.13"
# dependencies = ["pillow>=11", "numpy>=2"]
# ///
"""Procesa el logo original de Joyería Blanco (FR-042, research R-18).

Uso (desde la raíz del repositorio):  uv run tools/brand/procesar_logo.py

1. Aísla el disco negro del fondo casi blanco (relleno por inundación desde las esquinas) y estima
   centro y radio por momentos.
2. Neutraliza el brillo gris del bisel (sector superior izquierdo de la corona exterior), lejos del
   monograma y del texto "BLANCO JOYEROS", que está en el sector inferior derecho.
3. Fuerza a negro el filo exterior para evitar halos claros sobre fondo oscuro.
4. Aplica una máscara circular antialiasada (supermuestreo ×4), recorta y exporta el logo y los
   iconos de la aplicación.
"""

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[2]
ORIGEN = RAIZ / "tools/brand/fuente/logo-original.png"
WEB = RAIZ / "joyeriablanco_web"
DESTINO_LOGO = WEB / "src/assets/brand/logo.png"
PUBLICO = WEB / "public"
FONDO_APP = (0x10, 0x13, 0x19)  # token `background` de docs/DESIGN.md

UMBRAL_FONDO = 225  # luminancia por encima de la cual un píxel es fondo
CORONA_BRILLO = (0.86, 0.89)  # inicio (fundido) de la corona donde se neutraliza el brillo
SECTOR_BRILLO = (25.0, 240.0)  # grados (0 = derecha, sentido antihorario con y hacia arriba)
FUNDIDO_ANGULAR = 10.0
FILO_NEGRO_PX = 4.0
RECORTE_BORDE_PX = 1.5
SUPERMUESTREO = 4


def luminancia(rgb: np.ndarray) -> np.ndarray:
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def estimar_disco(rgb: np.ndarray) -> tuple[float, float, float]:
    alto, ancho = rgb.shape[:2]
    luz = Image.fromarray(((luminancia(rgb) > UMBRAL_FONDO) * 255).astype("uint8"), mode="L").copy()
    for esquina in [(0, 0), (ancho - 1, 0), (0, alto - 1), (ancho - 1, alto - 1)]:
        ImageDraw.floodfill(luz, esquina, 128, thresh=0)
    disco = np.array(luz) != 128
    ys, xs = np.nonzero(disco)
    return float(xs.mean()), float(ys.mean()), math.sqrt(disco.sum() / math.pi)


def limpiar(rgb: np.ndarray, cx: float, cy: float, radio: float) -> np.ndarray:
    alto, ancho = rgb.shape[:2]
    yy, xx = np.mgrid[0:alto, 0:ancho].astype(float)
    dx, dy = xx - cx, cy - yy
    rr = np.hypot(dx, dy) / radio
    angulo = (np.degrees(np.arctan2(dy, dx)) + 360.0) % 360.0

    ini, fin = SECTOR_BRILLO
    peso_ang = np.clip(
        np.minimum(angulo - ini, fin - angulo) / FUNDIDO_ANGULAR, 0.0, 1.0
    )
    peso_rad = np.clip((rr - CORONA_BRILLO[0]) / (CORONA_BRILLO[1] - CORONA_BRILLO[0]), 0.0, 1.0)
    peso = (peso_ang * peso_rad)[..., None]
    limpio = rgb * (1.0 - peso)  # funde hacia negro

    filo = (np.hypot(dx, dy) > radio - FILO_NEGRO_PX)[..., None]
    return np.where(filo, 0.0, limpio)


def mascara(alto: int, ancho: int, cx: float, cy: float, radio: float) -> Image.Image:
    s = SUPERMUESTREO
    grande = Image.new("L", (ancho * s, alto * s), 0)
    r = (radio - RECORTE_BORDE_PX) * s
    ImageDraw.Draw(grande).ellipse((cx * s - r, cy * s - r, cx * s + r, cy * s + r), fill=255)
    return grande.resize((ancho, alto), Image.Resampling.LANCZOS)


def con_fondo(logo: Image.Image, lado: int, margen: float) -> Image.Image:
    lienzo = Image.new("RGBA", (lado, lado), (*FONDO_APP, 255))
    interior = round(lado * (1 - 2 * margen))
    pieza = logo.resize((interior, interior), Image.Resampling.LANCZOS)
    desplazamiento = (lado - interior) // 2
    lienzo.alpha_composite(pieza, (desplazamiento, desplazamiento))
    return lienzo


def main() -> None:
    original = Image.open(ORIGEN).convert("RGB")
    rgb = np.asarray(original).astype(float)
    cx, cy, radio = estimar_disco(rgb)
    print(f"Disco: centro=({cx:.1f}, {cy:.1f}) radio={radio:.1f} px")

    limpio = Image.fromarray(np.clip(limpiar(rgb, cx, cy, radio), 0, 255).astype("uint8"), "RGB")
    rgba = limpio.convert("RGBA")
    rgba.putalpha(mascara(original.height, original.width, cx, cy, radio))

    lado = math.ceil(radio) + 2
    caja = (round(cx) - lado, round(cy) - lado, round(cx) + lado, round(cy) + lado)
    logo = rgba.crop(caja)

    DESTINO_LOGO.parent.mkdir(parents=True, exist_ok=True)
    PUBLICO.mkdir(parents=True, exist_ok=True)
    logo.resize((512, 512), Image.Resampling.LANCZOS).save(DESTINO_LOGO, optimize=True)
    for tam, nombre in [(192, "icon-192.png"), (512, "icon-512.png"), (32, "favicon-32.png")]:
        logo.resize((tam, tam), Image.Resampling.LANCZOS).save(PUBLICO / nombre, optimize=True)
    logo.resize((256, 256), Image.Resampling.LANCZOS).save(
        PUBLICO / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)]
    )
    con_fondo(logo, 180, 0.06).convert("RGB").save(PUBLICO / "apple-touch-icon.png", optimize=True)

    manifiesto = {
        "name": "Joyería Blanco · Gestión",
        "short_name": "Joyería Blanco",
        "lang": "es",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#101319",
        "theme_color": "#101319",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }
    (PUBLICO / "manifest.webmanifest").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Logo: {DESTINO_LOGO.relative_to(RAIZ)}; iconos en {PUBLICO.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
