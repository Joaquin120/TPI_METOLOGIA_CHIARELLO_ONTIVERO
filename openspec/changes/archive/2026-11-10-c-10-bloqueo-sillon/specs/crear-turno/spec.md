# Spec Delta

## ADDED Requirements

### Requirement: Rechazo de alta de turno si el sillón está bloqueado por mantenimiento
El sistema SHALL verificar, antes de persistir un nuevo turno, que el sillón seleccionado no posea ningún bloqueo temporal por mantenimiento que se solape con el intervalo semiabierto solicitado `[hora_inicio, hora_fin)`; y SHALL rechazar la solicitud con código HTTP 409 y código de error "SILLON_BLOQUEADO" si el sillón se encuentra bloqueado.

#### Scenario: Rechazo de creación de turno en sillón bloqueado (Error de Negocio)
- **GIVEN** un sillón 1 con un bloqueo de mantenimiento registrado el "2026-11-20" de "08:00" a "12:00"
- **WHEN** la recepcionista solicita crear un turno para el "Dr. Ejemplo" en el sillón 1 el "2026-11-20" de "09:00" a "09:30"
- **THEN** el sistema rechaza la creación con código HTTP 409 y código de error "SILLON_BLOQUEADO"

#### Scenario: Alta exitosa de turno en horario contiguo a un bloqueo (Caso de Borde)
- **GIVEN** un sillón 1 bloqueado el "2026-11-20" de "08:00" a "12:00"
- **WHEN** se solicita agendar un turno en el sillón 1 el "2026-11-20" de "12:00" a "12:30"
- **THEN** el sistema acepta el turno con código HTTP 201 confirmando la validez del límite contiguo semiabierto
