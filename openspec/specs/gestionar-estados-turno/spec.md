# gestionar-estados-turno Specification

## Purpose
Administrar el ciclo de vida del turno odontológico: aplicar únicamente las transiciones válidas entre `PENDIENTE`, `CONFIRMADO`, `CANCELADO` y `COMPLETADO`, rechazar con `TransicionInvalidaError` cualquier transición no permitida y liberar al profesional y al sillón al cancelar para permitir re-agendar en el intervalo semiabierto `[inicio, fin)`.

## Requirements

### Requirement: Transiciones válidas del ciclo de vida del turno
El sistema SHALL aplicar solo las transiciones de la matriz RN-03: `confirmar()` lleva `PENDIENTE` → `CONFIRMADO`; `cancelar()` lleva `PENDIENTE` o `CONFIRMADO` → `CANCELADO`; `completar()` lleva `CONFIRMADO` → `COMPLETADO`. Cada transición válida SHALL devolver el turno con el estado actualizado y sin alterar sus recursos asignados.

#### Scenario: Confirmación de un turno pendiente (Camino Feliz)
- **GIVEN** que existe un turno registrado con estado "PENDIENTE" para el "Dr. Pérez" en el "Sillón 1" el "2026-11-01" de "10:00" a "10:30"
- **WHEN** se ejecuta la acción `confirmar()` sobre ese turno
- **THEN** el turno pasa al estado "CONFIRMADO" y el sistema lo conserva registrado con el mismo profesional, sillón e intervalo

#### Scenario: Finalización de un turno confirmado (Camino Feliz)
- **GIVEN** que existe un turno en estado "CONFIRMADO" para el "Dr. Pérez" en el "Sillón 1" el "2026-11-01" de "10:00" a "10:30"
- **WHEN** se ejecuta la acción `completar()` sobre ese turno
- **THEN** el turno pasa al estado "COMPLETADO" y deja de considerarse activo

### Requirement: Rechazo de transiciones inválidas desde estados finales
Los estados `CANCELADO` y `COMPLETADO` SHALL ser absorbentes: el sistema SHALL rechazar con `TransicionInvalidaError` cualquier transición originada en ellos, y el turno SHALL permanecer en su estado actual sin modificación alguna.

#### Scenario: Completar un turno cancelado se rechaza (Error de Negocio)
- **GIVEN** que existe un turno en estado final "CANCELADO"
- **WHEN** se intenta la transición `completar()` (de "CANCELADO" a "COMPLETADO")
- **THEN** el sistema rechaza la operación lanzando `TransicionInvalidaError` y el turno permanece en estado "CANCELADO"

#### Scenario: Cancelar un turno completado se rechaza (Error de Negocio)
- **GIVEN** que existe un turno en estado final "COMPLETADO"
- **WHEN** se intenta la transición `cancelar()` (de "COMPLETADO" a "CANCELADO")
- **THEN** el sistema rechaza la operación lanzando `TransicionInvalidaError` y el turno permanece en estado "COMPLETADO"

### Requirement: Liberación de recursos por cancelación
Al pasar a `CANCELADO`, el turno SHALL dejar de considerarse activo: el sistema SHALL dejar de bloquear al profesional y al sillón de forma simultánea e independiente en el intervalo semiabierto `[T_inicio, T_fin)`, evaluado con el criterio `inicio_a < fin_b AND fin_a > inicio_b` (D-07). Ambos recursos SHALL quedar disponibles de inmediato para nuevas reservas (RN-04, doble validación).

#### Scenario: La cancelación libera el intervalo del profesional y del sillón (Esperado)
- **GIVEN** un turno en estado "CONFIRMADO" que ocupa el intervalo "10:00" a "10:30" del "2026-11-01" con el profesional "Dr. Pérez" y el "Sillón 1"
- **WHEN** se ejecuta la acción `cancelar()` sobre ese turno
- **THEN** el turno pasa a estado "CANCELADO" y ni el profesional ni el sillón quedan bloqueados en el intervalo ["10:00", "10:30")

#### Scenario: Re-reserva del mismo profesional y sillón dentro del intervalo liberado (Caso de Borde)
- **GIVEN** que un turno del "Dr. Pérez" en el "Sillón 1" del "2026-11-01" de "10:00" a "10:30" acaba de ser cancelado
- **WHEN** se solicita un nuevo turno para ese mismo profesional y ese mismo sillón de "10:15" a "10:45", dentro del intervalo liberado
- **THEN** la creación es exitosa: el turno cancelado no bloquea (RN-04) y el solapamiento se evalúa con el criterio semiabierto `inicio_a < fin_b AND fin_a > inicio_b` (D-07)

#### Scenario: Re-reserva contigua que empieza exactamente en T_fin del turno cancelado (Caso de Borde)
- **GIVEN** que un turno del "Dr. Pérez" en el "Sillón 1" del "2026-11-01" de "10:00" a "10:30" acaba de ser cancelado
- **WHEN** se solicita un nuevo turno para ese mismo profesional y ese mismo sillón que comienza exactamente en "10:30" (el `T_fin` del turno cancelado)
- **THEN** la creación es exitosa: `fin_del_turno_cancelado == inicio_del_nuevo` no constituye solapamiento en intervalos semiabiertos (RN-02 / D-07) y el nuevo turno queda en estado "CONFIRMADO"
