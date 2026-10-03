# Specification Quality Checklist: Presupuestos con conversión en factura

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-02
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

## Notes

- Las decisiones de alcance se tomaron con el responsable antes de especificar (Clarifications,
  2026-10-02, y constitución 2.3.0). Por eso no quedan marcas [NEEDS CLARIFICATION].
- Como en 002 y 003, se mantienen a propósito algunos términos con valor normativo o de dominio:
  - Las series `PRE`, `FAC` y `REC`.
  - El registro de alta y la huella, para dejar claro qué NO genera un presupuesto.
  - Las expresiones literales del documento impreso.
- `/speckit.clarify` (2026-10-02) resolvió:
  - La conversión mediante un borrador de factura vinculado.
  - El bloqueo del presupuesto mientras ese borrador existe.
  - La conversión de un presupuesto caducado.
  - Los permisos.
  - La validez por defecto y el pie propio.
- Quedan como supuestos documentados, de bajo impacto:
  - El domicilio del cliente para emitir un presupuesto.
  - El IVA aplicable si cambia antes de la conversión, que sigue la regla de 002.
  - Qué presupuestos suman en el listado impreso.
