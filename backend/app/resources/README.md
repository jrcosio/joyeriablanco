# Recursos del backend

## `contrasenas_comunes.txt` (research R-7, FR-008)

Lista de contraseñas comunes que la política de contraseñas rechaza (comparación sin distinguir
mayúsculas).

- **Fuente principal**: UK National Cyber Security Centre (NCSC), *PwnedPasswordsTop100k.txt*.
  - Top 100.000 contraseñas del conjunto de datos de Have I Been Pwned.
  - URL oficial: `https://www.ncsc.gov.uk/static-assets/documents/PwnedPasswordsTop100k.txt`.
  - Licencia: Open Government Licence v3.0.
- **Obtención (2026-09-27)**: la URL oficial respondía 404 ("Site currently unavailable"), así que
  se usó la copia archivada de esa misma URL en el Internet Archive:
  `https://web.archive.org/web/2024id_/https://www.ncsc.gov.uk/static-assets/documents/PwnedPasswordsTop100k.txt`.
  - SHA-256 del fichero descargado:
    `f68c289c93bbaefd6f6700c7ba3035077ffe4d402b571708ff595258f2d93e15`.
- **Tratamiento**: se eliminan las líneas de cabecera `***`, los retornos de carro y las líneas
  vacías, se pasa todo a minúsculas y se quitan los duplicados.
- **Añadidos propios**: términos del negocio (`joyeria`, `blanco`, `joyeriablanco`, `contraseña`,
  `verifactu`…) al final del fichero.
