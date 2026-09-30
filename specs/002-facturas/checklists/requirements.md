# Specification Quality Checklist: Facturación con registro Verifactu

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-28
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

- **Marcadores de especificación** (2026-09-28): se resolvieron los tres [NEEDS CLARIFICATION]
  iniciales con el responsable.
  - **Modalidad**: pendiente de la asesoría.
  - **Tipos de factura**: solo completas (F1).
  - **«Modificar»**: se pregunta el motivo, con la consulta intermedia documentada.
  - **Número**: automático, con ajuste al alza del contador.
- **Referencias técnicas que se mantienen a propósito**:
  - FR-022 cita "el patrón de la auditoría de 001" y FR-031 "la consola de administración del
    servidor", igual que hizo la spec de 001. Son referencias a capacidades ya existentes del
    sistema, no decisiones de tecnología.
  - SC-005 habla de "credenciales del servicio y del propietario de los datos", en los mismos
    términos que 001, SC-007.
- **Pendiente de verificar en el research del plan** (constitución IV): los campos de F-1, el
  algoritmo de F-2, las tolerancias y reglas de fecha de F-3, el texto del BOE de F-8 y la
  codificación de la rectificativa por sustitución. La spec no deduce ninguno de memoria.
- **Constitución**: la opción elegida para el contador (ajuste al alza en cualquier momento) deja
  huecos dentro del sistema. Contradice el «sin huecos» de la restricción "Numeración" de la
  constitución 2.1.0, que remitía a esta spec, y exige enmendarla (2.2.0) antes del plan.
- **Revalidación del 2026-09-30 (ajuste de cierre: IVA libre, sin clave de régimen, IBAN y oro de
  inversión)**: todos los puntos siguen cumpliéndose.
  - Cambian FR-001, FR-013, FR-016, FR-023, FR-033 y FR-037. Entran FR-052 y FR-053, los
    escenarios US1-7, US1-8, US2-10 y US5-9, los casos límite nuevos y SC-012 y SC-013.
  - Hay cero marcadores [NEEDS CLARIFICATION]: las cuatro decisiones del responsable están en la
    sesión de Clarifications del 2026-09-30.
  - Los nombres de campos del registro (`ClaveRegimen`, `OperacionExenta`…) son los de los diseños
    oficiales, igual que en el resto de la spec (constitución IV). No son decisiones de tecnología.
  - **Pendiente de verificar en el research del plan** (constitución IV): en F-1, las filas del
    desglose `CalificacionOperacion` y `OperacionExenta` («obligatorios y alternativos») y el orden
    de sus campos. En F-3, el texto completo de §15.4 a §15.6. También la validación del IBAN según
    ISO 13616.
