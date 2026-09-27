# Specification Quality Checklist: Cimientos del sistema, seguridad de acceso y gestión de clientes

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-27
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Constitution Conformance (1.1.0)

- [x] **I (SDD)**: rama `001-cimientos-clientes` creada a mano, spec en `specs/001-cimientos-clientes/`.
- [x] **IV (Verifactu)**: los formatos de la identificación del cliente se toman de fuente oficial y
      se citan con URL, versión y fecha de consulta (F-1, F-2). Lo que no se pudo verificar se lista
      como pendiente de verificación en plan, no se deduce.
- [x] **VII (tests obligatorios)**: se deja constancia de que ninguno de los cuatro tests aplica.
- [x] **VIII (español)**: dominio, mensajes e interfaz en español.
- [x] **Sistema de diseño**: las desviaciones del mockup están justificadas en tabla; ninguna
      desviación de `docs/DESIGN.md`.

## Notes

- **Iteración 1 de la validación**:
  - SC-011 decía "máxima calificación sin avisos graves", que no es medible. Se ha reformulado como
    "calificación A o superior".
  - El resto de puntos pasan sin cambios.
- **Revalidación del 2026-09-28** (ajuste de cierre, eliminación de usuarios):
  - Se añaden FR-061, SC-013, los escenarios 10–12 de US5, un caso límite de concurrencia y la
    sesión de clarificación del 2026-09-28. Se ajustan FR-014, FR-017, FR-020, FR-050, FR-058 y la
    entidad Usuario.
  - Todos los puntos siguen pasando: sin marcadores pendientes, requisitos comprobables y criterio
    SC-013 medible y sin detalles de implementación.
- **Referencias técnicas permitidas**: la spec solo menciona el nombre de fichero y la URL de la
  fuente oficial AEAT, que la constitución (principio IV) exige citar. No es un detalle de
  implementación.
- **Candidatos para `/speckit.clarify`**: se dejaron como supuestos y no como marcadores, porque
  tienen un valor por defecto razonable:
  - Unicidad de la identificación.
  - Exclusión del tipo L7 "07 No censado".
  - Tiempos de sesión y umbrales de bloqueo.
  - Consulta de la auditoría desde la interfaz, que queda fuera de alcance.
- **Pendientes de verificar en `/speckit.plan`**:
  - El cálculo oficial del carácter de control del NIF.
  - Las reglas de `IDOtro` en *Validaciones y errores* v1.2.2.
  - La lista oficial de provincias.
