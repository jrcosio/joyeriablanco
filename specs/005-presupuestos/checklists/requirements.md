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
- Supuestos que conviene confirmar en `/speckit.clarify`:
  - Conversión directa o mediante un borrador de factura.
  - Conversión de un presupuesto caducado, y si una conversión es única.
  - Permisos de cada operación.
  - Validez por defecto y pie propio del presupuesto.
  - Domicilio del cliente para emitir un presupuesto.
  - IVA aplicable si cambia antes de la conversión.
  - Qué presupuestos suman en el listado impreso.
