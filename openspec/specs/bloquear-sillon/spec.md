# bloquear-sillon Specification

## Purpose
Permite gestionar bloqueos temporales de sillones y boxes de atención odontológica por mantenimiento preventivo, desinfección o reparaciones técnicas en intervalos semiabiertos, impidiendo solapamientos con turnos activos o bloqueos preexistentes, con autorización restringida por rol y trazabilidad inmutable.

## Requirements

### Requirement: Registro de bloqueo de sillón por mantenimiento
El sistema SHALL exponer un endpoint `POST /api/v1/bloqueos` que permita registrar un bloqueo temporal de sillón indicando `sillon_id`, `fecha`, `hora_inicio`, `hora_fin` y `motivo`, requiriendo formato de intervalo semiabierto `[hora_inicio, hora_fin)` con `hora_inicio < hora_fin`, respondiendo con código HTTP 201 y la entidad creada.

#### Scenario: Registro exitoso de bloqueo de sillón (Camino Feliz)
- **GIVEN** un administrador autenticado y un sillón activo en el tenant sin turnos ni bloqueos en el horario solicitado
- **WHEN** el administrador envía `POST /api/v1/bloqueos` con sillon_id 1, fecha "2026-11-20", hora_inicio "08:00", hora_fin "12:00" y motivo "Mantenimiento preventivo anual de turbina"
- **THEN** el sistema responde con código HTTP 201, crea el bloqueo con un id asignado y estado persistido

#### Scenario: Bloqueos contiguos en el límite exacto son válidos (Caso de Borde)
- **GIVEN** un bloqueo existente para el sillón 1 el "2026-11-20" de "08:00" a "10:00"
- **WHEN** el administrador solicita un nuevo bloqueo para el sillón 1 de "10:00" a "12:00" en la misma fecha
- **THEN** el sistema acepta el registro con código HTTP 201 porque los intervalos semiabiertos `[inicio, fin)` no se solapan en el límite contiguo

#### Scenario: Rechazo por superposición con otro bloqueo existente (Error de Negocio)
- **GIVEN** un bloqueo existente en el sillón 1 el "2026-11-20" de "08:00" a "12:00"
- **WHEN** se intenta registrar otro bloqueo para el sillón 1 el "2026-11-20" de "11:00" a "13:00"
- **THEN** el sistema rechaza la solicitud con código HTTP 409 y código de error "BLOQUEO_SOLAPADO"

### Requirement: Impedir bloqueo de sillón ante turnos activos en el intervalo (RP-07)
El sistema SHALL validar que no existan turnos activos (`PENDIENTE` o `CONFIRMADO`) asignados al sillón dentro del intervalo solicitado, y SHALL rechazar la creación del bloqueo si existe conflicto para proteger la agenda de los pacientes.

#### Scenario: Intento de bloqueo sobre sillón con turno activo se rechaza (Error de Negocio)
- **GIVEN** un turno confirmado asignado al sillón 1 el "2026-11-20" de "09:00" a "10:00"
- **WHEN** el administrador intenta crear un bloqueo para el sillón 1 el "2026-11-20" de "08:00" a "12:00"
- **THEN** el sistema rechaza la solicitud con código HTTP 409 y código de error "CONFLICTO_TURNOS_EXISTENTES" sin registrar el bloqueo

#### Scenario: Bloqueo permitido si los turnos existentes en el intervalo están cancelados (Caso de Borde)
- **GIVEN** un turno en estado "CANCELADO" en el sillón 1 el "2026-11-20" de "09:00" a "10:00"
- **WHEN** el administrador solicita crear un bloqueo para el sillón 1 el "2026-11-20" de "08:00" a "12:00"
- **THEN** el sistema acepta el bloqueo con código HTTP 201 confirmando que los turnos cancelados no impiden el bloqueo

### Requirement: Consulta y listado de bloqueos de sillón
El sistema SHALL exponer un endpoint `GET /api/v1/bloqueos` que permita consultar la colección de bloqueos del tenant autenticado, admitiendo filtros opcionales por `sillon_id`, `fecha_desde` y `fecha_hasta`, respondiendo con código HTTP 200 y una lista JSON.

#### Scenario: Listado de bloqueos del tenant con filtros (Camino Feliz)
- **GIVEN** un usuario autenticado con rol `Administrador` o `Recepcionista` en una clínica con bloqueos registrados
- **WHEN** solicita `GET /api/v1/bloqueos?sillon_id=1`
- **THEN** el sistema responde con código HTTP 200 y la lista de bloqueos pertenecientes exclusivamente a ese sillón y tenant

#### Scenario: Aislamiento multi-tenant en consulta de bloqueos (Error de Negocio)
- **GIVEN** bloqueos registrados en el Tenant A y en el Tenant B
- **WHEN** un usuario del Tenant A consulta `GET /api/v1/bloqueos`
- **THEN** el sistema devuelve únicamente los bloqueos correspondientes al Tenant A

### Requirement: Liberación o anulación anticipada de bloqueo de sillón
El sistema SHALL exponer un endpoint `DELETE /api/v1/bloqueos/{id}` que permita al Administrador anular o dar por finalizado un bloqueo de sillón existente, liberando de inmediato el intervalo para permitir la asignación de turnos.

#### Scenario: Eliminación exitosa de un bloqueo (Camino Feliz)
- **GIVEN** un bloqueo existente con id 5 en el sillón 1
- **WHEN** el administrador envía `DELETE /api/v1/bloqueos/5`
- **THEN** el sistema elimina el bloqueo, responde con código HTTP 200 o 204, y el sillón 1 queda disponible en ese horario

#### Scenario: Intento de eliminar bloqueo inexistente o de otro tenant devuelve 404 (Error de Negocio)
- **GIVEN** un id de bloqueo inexistente o perteneciente a otro tenant
- **WHEN** el administrador envía `DELETE /api/v1/bloqueos/{id}`
- **THEN** el sistema responde con código HTTP 404 y código de error "BLOQUEO_NO_ENCONTRADO"

### Requirement: Control de acceso RBAC y auditoría inmutable
La creación y eliminación de bloqueos SHALL estar restringida exclusivamente al rol `Administrador`; la consulta SHALL admitir `Administrador` y `Recepcionista`; y toda creación o eliminación exitosa SHALL registrar un evento en la bitácora inmutable de auditoría.

#### Scenario: Acceso denegado para rol no autorizado en gestión de bloqueos (Error de Negocio)
- **GIVEN** un usuario autenticado con rol "Recepcionista" o "Profesional"
- **WHEN** intenta enviar `POST /api/v1/bloqueos` o `DELETE /api/v1/bloqueos/{id}`
- **THEN** el sistema rechaza la solicitud con código HTTP 403 y código de error "ACCESO_DENEGADO"

#### Scenario: Registro inmutable en auditoría al crear y eliminar bloqueos (Camino Feliz)
- **GIVEN** un administrador que crea exitosamente un bloqueo y posteriormente lo elimina
- **WHEN** se consulta la bitácora de auditoría
- **THEN** constan los eventos "CREAR_BLOQUEO_SILLON" y "ELIMINAR_BLOQUEO_SILLON" con el usuario_id y entidad_id asociados
