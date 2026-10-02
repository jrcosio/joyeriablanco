# Fuentes de los documentos impresos (003, research R-4)

Tipografías de `docs/DESIGN.md` (Bodoni Moda y Manrope) para los PDF que genera WeasyPrint. Son los
mismos ficheros de Fontsource 5.3.0 que usa la web, en WOFF2 estático y con los subconjuntos
`latin` y `latin-ext`.

- **Licencia**: SIL Open Font License 1.1.
  - [`OFL-manrope.txt`](OFL-manrope.txt): Manrope, © 2019 The Manrope Project Authors.
  - [`OFL-bodoni-moda.txt`](OFL-bodoni-moda.txt): Bodoni Moda, © 2020 The Bodoni Moda Project
    Authors.
- **Origen (2026-10-02)**:
  - Manrope: `https://cdn.jsdelivr.net/npm/@fontsource/manrope@5.3.0/files/` (paquete estático, no
    el variable de la web).
  - Bodoni Moda: `https://cdn.jsdelivr.net/npm/@fontsource/bodoni-moda@5.3.0/files/`. Los ficheros
    `latin` son idénticos a los de `joyeriablanco_web/node_modules/@fontsource/bodoni-moda`.
- **Rangos** (`unicode-range` de Fontsource 5.3.0, que repite `base.html`):
  - `latin`: `U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304,
    U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD`.
  - `latin-ext`: `U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308,
    U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113,
    U+2C60-2C7F, U+A720-A7FF`.

| Fichero | SHA-256 |
|---|---|
| `bodoni-moda-latin-400-normal.woff2` | `e2863d3bbe2e094f1ce98053ee3c6200cfa35f82b9f4cc6fd95fbaead4125d4f` |
| `bodoni-moda-latin-500-normal.woff2` | `ec5b785abb85d087b5101a74671933b1bab5f96d9d85f868cc33964e69758748` |
| `bodoni-moda-latin-ext-400-normal.woff2` | `a774674421465c1b1d81a47523a5260cbb71cb2194f3a56dbf8d2e37352f167a` |
| `bodoni-moda-latin-ext-500-normal.woff2` | `b50625079c130893bf657f92b9a8ef280bfe5069c8d9c81fc4557e2ddf985e7b` |
| `manrope-latin-400-normal.woff2` | `849290ef12a2eeb9af5c11924120d11aa4ae8b435ed3347d7fc8bc240c293ca3` |
| `manrope-latin-600-normal.woff2` | `f7ac6258da20ab7541939b59851155753d1d24f1b30cbcb949077a3faa3d1593` |
| `manrope-latin-700-normal.woff2` | `d2a12c85a831e4b5db341767d0347fa3d1361d22a1fcb3e361a16b6c90080f71` |
| `manrope-latin-ext-400-normal.woff2` | `72c5354a6f814f3bd38dc3d8caee774f7557b301e69d8428e677b7b73d58d9ee` |
| `manrope-latin-ext-600-normal.woff2` | `ff679412842fc3b5ce2dfad626db5261a4e663dcfd1bf1209bdfc61c2b2f37e6` |
| `manrope-latin-ext-700-normal.woff2` | `dc7c46d7eb269cc90650d7f70cf49aafa39a98444e6882cc84096acbc156bfcd` |
