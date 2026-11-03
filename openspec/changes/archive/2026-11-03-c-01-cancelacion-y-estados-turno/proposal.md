# Proposal

## Why

El alta de turnos (`crear-turno`) registra turnos pero no existe ninguna forma de cambiar su estado después: `ServicioTurnos` solo valida solapamientos al agendar. Sin el ciclo de vida del turno (RN-03) ni la liberación por cancelación (RN-04), la agenda queda bloqueada por turnos que ya no van a ocurrir y el camino crítico MVP (`C-01 → C-02 → C-03`) no puede arrancar.

## What Changes

- Máquina de estados del turno con las constantes `PENDIENTE`, `CONFIRMADO`, `CANCELADO` y `COMPLETADO`, más la matriz de transiciones válidas de RN-03 como lista blanca (acciones: Confirmar, Cancelar, Completar).
- `ServicioTurnos` (`backend/src/domain/services.py`) gana tres métodos de dominio — `confirmar()`, `cancelar()` y `completar()` — que aplican la matriz y rechazan cualquier transición no listada.
- Nueva excepción de dominio `TransicionInvalidaError` en `backend/src/domain/exceptions.py`, con el mismo contrato que las excepciones existentes: hereda de `Exception`, `__init__(self, mensaje: str = "<mensaje por defecto>")` en español y docstring explicativo.
- El filtro de solapamiento de `agendar_turno()` deja de considerar los turnos `CANCELADO` y `COMPLETADO`: solo los turnos **activos** (`PENDIENTE`/`CONFIRMADO`) bloquean profesional y sillón (RN-04), liberando el intervalo semiabierto `[T_inicio, T_fin)` (D-07) de forma simultánea e independiente en ambos recursos (regla dura 2: doble validación).
- Tests nuevos con TDD: transiciones válidas e inválidas, liberación por cancelación con re-agenda en el mismo intervalo, estados finales absorbentes; los 8 tests actuales de `backend/tests/test_turnos.py` siguen en verde (regla dura 4: suite verde).
- **No se modifica** el estado inicial del alta: sigue siendo `CONFIRMADO` según la spec vigente `crear-turno`; `PA-13` continúa abierta y **no se resuelve** en este change.

## Capabilities

### New Capabilities

- `gestionar-estados-turno`: ciclo de vida del turno — transiciones válidas de RN-03, rechazo de transiciones inválidas con `TransicionInvalidaError` y liberación de profesional y sillón al cancelar (RN-04) sobre intervalos semiabiertos `[inicio, fin)` (D-07).

### Modified Capabilities

_(ninguna)_

Los requisitos y escenarios de `crear-turno` siguen vigentes sin cambios: todos operan sobre turnos activos y la alta sigue registrando con estado `CONFIRMADO`. La precisión de que solo los turnos activos (`PENDIENTE`/`CONFIRMADO`) bloquean recursos queda especificada en la nueva capability `gestionar-estados-turno`, sin alterar la spec existente.

## Impact

- **Dominio**: `backend/src/domain/models.py` (constantes de estado; `Turno.estado` conserva el default `"CONFIRMADO"`), `backend/src/domain/services.py` (`agendar_turno()` suma filtro por estado activo; nuevos `confirmar()`, `cancelar()`, `completar()`), `backend/src/domain/exceptions.py` (nueva `TransicionInvalidaError`).
- **Tests**: tests nuevos en `backend/tests/` (p. ej. `test_estados_turno.py`); los 8 tests existentes de `test_turnos.py` no se modifican y deben seguir verdes.
- **Specs**: nueva capability `gestionar-estados-turno`; `crear-turno` no cambia.
- **Sin impacto** en API HTTP, persistencia, dependencias externas ni frontend: la persistencia llega en `C-02`, la API desacoplada en `C-03`/`C-05`.
- **No se tocan** `CHANGES.md` ni el change archivado `2026-10-15-crear-turno-sin-solapamientos`; este change es su continuación directa (sin dependencias nuevas).
