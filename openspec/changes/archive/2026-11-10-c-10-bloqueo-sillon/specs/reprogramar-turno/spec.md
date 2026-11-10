# Spec Delta

## ADDED Requirements

### Requirement: Rechazo de reprogramación si el sillón de destino está bloqueado por mantenimiento
El sistema SHALL verificar, al reprogramar un turno existente a un nuevo horario o sillón, que el sillón no presente bloqueos temporales por mantenimiento que se solapen con el nuevo intervalo semiabierto `[hora_inicio, hora_fin)`; y SHALL rechazar la solicitud con código HTTP 409 y código de error "SILLON_BLOQUEADO" en caso de conflicto.

#### Scenario: Rechazo de reprogramación hacia sillón bloqueado (Error de Negocio)
- **GIVEN** un turno existente confirmado y un sillón 1 bloqueado el "2026-11-20" de "14:00" a "18:00"
- **WHEN** se solicita reprogramar el turno hacia el sillón 1 el "2026-11-20" de "15:00" a "16:00"
- **THEN** el sistema rechaza la reprogramación con código HTTP 409 y código de error "SILLON_BLOQUEADO" manteniendo inalterado el turno

#### Scenario: Reprogramación permitida en horario inmediatamente contiguo al bloqueo (Caso de Borde)
- **GIVEN** un sillón 1 bloqueado el "2026-11-20" de "14:00" a "18:00"
- **WHEN** se reprograma un turno hacia el sillón 1 el "2026-11-20" de "18:00" a "18:30"
- **THEN** el sistema responde con código HTTP 200 y actualiza el horario del turno exitosamente
