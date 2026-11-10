# Spec Delta

## Purpose

Permite reprogramar turnos existentes de forma in-place manteniendo su identidad y trazabilidad histórica, validando la disponibilidad de profesional y sillón de forma simultánea e independiente, liberando de inmediato el intervalo horario previo y garantizando aislamiento multi-tenant y control de acceso RBAC.

## ADDED Requirements

### Requirement: Reprogramación exitosa in-place de un turno activo
El sistema SHALL permitir la reprogramación de turnos existentes en estado `PENDIENTE` o `CONFIRMADO` a un nuevo intervalo horario (`fecha`, `hora_inicio`, `hora_fin`), preservando el identificador único (`id`) del turno, su estado actual y sus datos de paciente, liberando de inmediato el horario previo para nuevas asignaciones.

#### Scenario: Reprogramación exitosa a un nuevo intervalo libre (Camino Feliz)
- **GIVEN** un turno confirmado con id 1 registrado el "2026-11-01" de "10:00" a "10:30" para "Dr. Ejemplo" en "Sillón 1"
- **WHEN** la recepcionista solicita reprogramar el turno al "2026-11-01" de "14:00" a "14:30" manteniendo profesional y sillón
- **THEN** el sistema responde con código HTTP 200, el turno conserva su id 1, actualiza fecha y horas, y permanece en estado "CONFIRMADO"

#### Scenario: Liberación inmediata del intervalo anterior para nuevas reservas (Camino Feliz)
- **GIVEN** un turno con id 1 reprogramado exitosamente del horario "10:00–10:30" al horario "14:00–14:30" el día "2026-11-01"
- **WHEN** se solicita crear un nuevo turno para otro paciente con "Dr. Ejemplo" y "Sillón 1" el "2026-11-01" de "10:00" a "10:30"
- **THEN** el sistema acepta el alta con código HTTP 201 confirmando que el horario anterior quedó plenamente liberado

#### Scenario: Reprogramación con cambio opcional de profesional y sillón (Camino Feliz)
- **GIVEN** un turno con id 1 asignado a "Dr. Ejemplo" y "Sillón 1"
- **WHEN** la recepcionista solicita reprogramar indicando un nuevo profesional "Dra. Colega" y un nuevo sillón "Sillón 2" en un horario libre
- **THEN** el sistema actualiza tanto los recursos asignados como el intervalo horario y responde con código HTTP 200

### Requirement: Doble validación simultánea e independiente de recursos en el nuevo intervalo
El sistema SHALL validar que ni el profesional ni el sillón presenten solapamiento con otros turnos activos en el nuevo intervalo semiabierto `[hora_inicio, hora_fin)`. Ante conflictos simultáneos, SHALL aplicar la precedencia RN-09 reportando primero conflicto de profesional.

#### Scenario: Conflicto por profesional ocupado en el nuevo horario (Error de Negocio)
- **GIVEN** un turno activo del "Dr. Ejemplo" el "2026-11-01" de "14:00" a "15:00"
- **WHEN** se intenta reprogramar otro turno con el "Dr. Ejemplo" para el "2026-11-01" de "14:30" a "15:30"
- **THEN** el sistema rechaza la reprogramación con código HTTP 409 y código de error "SOLAPAMIENTO_PROFESIONAL"

#### Scenario: Conflicto por sillón ocupado en el nuevo horario (Error de Negocio)
- **GIVEN** un turno activo en el "Sillón 1" el "2026-11-01" de "14:00" a "15:00" con otro profesional
- **WHEN** se intenta reprogramar un turno hacia el "Sillón 1" el "2026-11-01" de "14:30" a "15:30"
- **THEN** el sistema rechaza la reprogramación con código HTTP 409 y código de error "SOLAPAMIENTO_SILLON"

#### Scenario: Conflicto simultáneo de profesional y sillón aplica precedencia RN-09 (Error de Negocio)
- **GIVEN** un turno existente de "Dr. Ejemplo" en "Sillón 1" el "2026-11-01" de "14:00" a "15:00"
- **WHEN** se intenta reprogramar un turno hacia ese mismo profesional y sillón en el intervalo "14:15" a "14:45"
- **THEN** el sistema rechaza con código HTTP 409 y código de error "SOLAPAMIENTO_PROFESIONAL"

#### Scenario: Turnos contiguos en el nuevo horario son válidos (Caso de Borde)
- **GIVEN** un turno existente de "10:00" a "10:30"
- **WHEN** se reprograma un turno hacia la franja "10:30" a "11:00" para el mismo profesional y sillón
- **THEN** el sistema acepta la reprogramación con código HTTP 200 porque los intervalos semiabiertos `[inicio, fin)` permiten contigüidad

### Requirement: Desplazamiento parcial en la misma franja horaria sin auto-solapamiento
Al validar la disponibilidad del nuevo horario, el sistema SHALL excluir el propio turno en reprogramación del conjunto de candidatos conflictivos, permitiendo desplazamientos parciales que solapen con su horario original.

#### Scenario: Desplazamiento parcial del horario original del propio turno (Caso de Borde)
- **GIVEN** un turno con id 1 de "10:00" a "11:00" con "Dr. Ejemplo" y "Sillón 1"
- **WHEN** se reprograma el turno con id 1 hacia el horario "10:30" a "11:30" manteniendo los mismos recursos
- **THEN** el sistema acepta la reprogramación con código HTTP 200 sin colisionar con el intervalo 10:00-11:00 que el propio turno ocupaba

### Requirement: Restricción de reprogramación por estado del turno
El sistema SHALL prohibir la reprogramación de turnos que se encuentren en estados terminales (`CANCELADO` o `COMPLETADO`), respondiendo con error de transición inválida y manteniendo inalterado el turno.

#### Scenario: Intento de reprogramar un turno cancelado se rechaza (Error de Negocio)
- **GIVEN** un turno en estado "CANCELADO"
- **WHEN** se solicita reprogramar dicho turno a cualquier nuevo horario
- **THEN** el sistema rechaza la solicitud con código HTTP 409 y código de error "TRANSICION_INVALIDA"

#### Scenario: Intento de reprogramar un turno completado se rechaza (Error de Negocio)
- **GIVEN** un turno en estado "COMPLETADO"
- **WHEN** se solicita reprogramar dicho turno a cualquier nuevo horario
- **THEN** el sistema rechaza la solicitud con código HTTP 409 y código de error "TRANSICION_INVALIDA"

### Requirement: Control de acceso RBAC y aislamiento multi-tenant
La reprogramación de turnos SHALL estar restringida a usuarios autenticados con rol `Recepcionista` o `Administrador` dentro de su propio tenant.

#### Scenario: Reprogramación permitida para roles autorizados (Camino Feliz)
- **GIVEN** una recepcionista o administradora autenticada con token JWT válido
- **WHEN** solicita reprogramar un turno perteneciente a su clínica
- **THEN** el sistema autoriza la operación y responde con código HTTP 200

#### Scenario: Acceso denegado para rol Profesional (Error de Negocio)
- **GIVEN** un usuario autenticado con rol "Profesional"
- **WHEN** intenta reprogramar un turno mediante la API
- **THEN** el sistema deniega la acción con código HTTP 403 y código de error "ACCESO_DENEGADO"

#### Scenario: Petición sin autenticación se rechaza (Error de Negocio)
- **WHEN** se invoca el endpoint de reprogramación sin cabecera Authorization o con token inválido
- **THEN** el sistema responde con código HTTP 401 y código de error "NO_AUTENTICADO"

#### Scenario: Turno inexistente o de otra clínica responde no encontrado (Error de Negocio)
- **GIVEN** un turno registrado en el Tenant B
- **WHEN** un usuario del Tenant A intenta reprogramar dicho turno
- **THEN** el sistema responde con código HTTP 404 y código de error "TURNO_NO_ENCONTRADO" sin alterar datos

### Requirement: Registro de trazabilidad y auditoría
El sistema SHALL registrar un evento en la tabla de auditoría para cada reprogramación exitosa, documentando el usuario responsable, el id del turno, el horario previo y el nuevo intervalo asignado.

#### Scenario: Auditoría inmutable de la reprogramación (Camino Feliz)
- **GIVEN** un usuario recepcionista con id 2 autenticado en el tenant 1
- **WHEN** reprograma exitosamente el turno 5 hacia un nuevo horario
- **THEN** se genera un registro en la tabla de auditoría con accion "REPROGRAMAR_TURNO", entidad "turno", entidad_id 5 y los detalles del cambio

### Requirement: Validación de formato y envelope uniforme de errores
El sistema SHALL validar la consistencia cronológica de la petición (`hora_inicio < hora_fin`, formato ISO de fecha `YYYY-MM-DD` y horas `HH:MM`), y SHALL unificar todas las respuestas de error bajo el envelope `{"error": {"code": "...", "message": "..."}}`.

#### Scenario: Horario con hora de inicio mayor o igual a hora de fin se rechaza (Error de Negocio)
- **WHEN** se envía una petición con hora_inicio "11:00" y hora_fin "10:30"
- **THEN** el sistema responde con código HTTP 422 y cuerpo JSON con envelope estándar de error
