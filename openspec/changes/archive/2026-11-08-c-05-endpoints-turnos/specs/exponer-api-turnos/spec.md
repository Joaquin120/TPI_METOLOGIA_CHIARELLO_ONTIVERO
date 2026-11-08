# Spec Delta

## MODIFIED Requirements

### Requirement: Listado de turnos acotado al tenant

`GET /api/v1/turnos` SHALL devolver `200` con la colección de turnos del tenant resuelto, y SHALL NOT incluir turnos de otros tenants. El endpoint SHALL admitir los parámetros de consulta opcionales `fecha` (YYYY-MM-DD), `profesional_id` (entero) y `sillon_id` (entero), aplicando conjunción lógica (AND) cuando se combinan múltiples filtros.

#### Scenario: Listado con turnos del tenant (Camino Feliz)
- **GIVEN** un tenant con dos turnos persistidos
- **WHEN** se solicita `GET /api/v1/turnos` con ese tenant
- **THEN** la respuesta es `200` con exactamente esos dos turnos y sus datos íntegros

#### Scenario: Turnos de otro tenant no aparecen (Error de Negocio)
- **GIVEN** un turno persistido en el tenant A y ningún turno en el tenant B
- **WHEN** se solicita `GET /api/v1/turnos` con el tenant B
- **THEN** la respuesta es `200` con una colección vacía

#### Scenario: Filtrado por fecha específica (Camino Feliz)
- **GIVEN** un tenant con turnos registrados en fechas "2026-11-01" y "2026-11-02"
- **WHEN** se solicita `GET /api/v1/turnos?fecha=2026-11-01`
- **THEN** la respuesta es `200` conteniendo únicamente los turnos del día "2026-11-01"

#### Scenario: Filtrado por profesional (Camino Feliz)
- **GIVEN** un tenant con turnos asignados a distintos profesionales
- **WHEN** una recepcionista solicita `GET /api/v1/turnos?profesional_id=1`
- **THEN** la respuesta es `200` conteniendo únicamente los turnos asignados al profesional con id 1

#### Scenario: Filtrado por sillón (Camino Feliz)
- **GIVEN** un tenant con turnos en distintos sillones
- **WHEN** se solicita `GET /api/v1/turnos?sillon_id=1`
- **THEN** la respuesta es `200` conteniendo únicamente los turnos asignados al sillón con id 1

#### Scenario: Filtrado combinado con conjunción lógica (Camino Feliz)
- **GIVEN** un tenant con múltiples turnos combinando fechas, profesionales y sillones
- **WHEN** se solicita `GET /api/v1/turnos?fecha=2026-11-01&profesional_id=1&sillon_id=2`
- **THEN** la respuesta es `200` conteniendo únicamente los turnos que cumplen simultáneamente todos los criterios

## ADDED Requirements

### Requirement: Restricción de agenda para rol Profesional

Cuando un usuario autenticado con rol `Profesional` consulta `GET /api/v1/turnos`, la API SHALL restringir automáticamente la respuesta a los turnos asignados a su propio `profesional_id`. Si se especifica un `profesional_id` distinto en la consulta, la API SHALL ignorarlo o responder `403` con código `ACCESO_DENEGADO`.

#### Scenario: Profesional consulta su propia agenda (Camino Feliz)
- **GIVEN** un usuario autenticado con rol "Profesional" vinculado al profesional_id 1
- **WHEN** solicita `GET /api/v1/turnos`
- **THEN** la respuesta es `200` y lista únicamente los turnos donde profesional_id es 1

#### Scenario: Profesional no puede acceder a turnos de otros profesionales (Seguridad)
- **GIVEN** un usuario autenticado con rol "Profesional" vinculado al profesional_id 1 y turnos del profesional 2
- **WHEN** intenta consultar `GET /api/v1/turnos?profesional_id=2`
- **THEN** la API rechaza con `403` y código "ACCESO_DENEGADO" o no devuelve ningún turno del profesional 2

### Requirement: Transición de estado del turno vía HTTP

`PATCH /api/v1/turnos/{id}/estado` SHALL validar el identificador del turno y el tenant resuelto, verificar los permisos del usuario (`Recepcionista` o `Administrador`), delegar la transición solicitada (`confirmar`, `cancelar` o `completar`) al dominio y responder `200` con el turno actualizado. Al cancelar, los recursos quedan inmediatamente disponibles para nuevas reservas.

#### Scenario: Cancelación exitosa de un turno y liberación de recursos (Camino Feliz)
- **GIVEN** un turno en estado "CONFIRMADO" en el tenant del usuario
- **WHEN** una recepcionista envía `PATCH /api/v1/turnos/{id}/estado` con acción "cancelar"
- **THEN** la respuesta es `200` con estado "CANCELADO" y los recursos quedan libres para agendar en ese horario

#### Scenario: Confirmación exitosa de un turno (Camino Feliz)
- **GIVEN** un turno en estado "PENDIENTE" en el tenant del usuario
- **WHEN** una recepcionista envía `PATCH /api/v1/turnos/{id}/estado` con acción "confirmar"
- **THEN** la respuesta es `200` con estado "CONFIRMADO"

#### Scenario: Finalización exitosa de un turno confirmado (Camino Feliz)
- **GIVEN** un turno en estado "CONFIRMADO" en el tenant del usuario
- **WHEN** un usuario autorizado envía `PATCH /api/v1/turnos/{id}/estado` con acción "completar"
- **THEN** la respuesta es `200` con estado "COMPLETADO"

#### Scenario: Turno inexistente o de otro tenant devuelve 404 (Error de Negocio)
- **GIVEN** un identificador de turno que no existe en el tenant autenticado
- **WHEN** se envía `PATCH /api/v1/turnos/{id}/estado` con acción "cancelar"
- **THEN** la respuesta es `404` con código de error "TURNO_NO_ENCONTRADO"

#### Scenario: Transición inválida rechazada por el dominio devuelve 409 (Error de Negocio)
- **GIVEN** un turno en estado final "CANCELADO"
- **WHEN** se envía `PATCH /api/v1/turnos/{id}/estado` con acción "completar"
- **THEN** la respuesta es `409` con código de error "TRANSICION_INVALIDA"

#### Scenario: Rol no autorizado para cambiar estado devuelve 403 (Error de Negocio)
- **GIVEN** un usuario autenticado con rol "Profesional"
- **WHEN** intenta enviar `PATCH /api/v1/turnos/{id}/estado` con acción "cancelar"
- **THEN** la respuesta es `403` con código de error "ACCESO_DENEGADO"

#### Scenario: Solicitud con acción no reconocida devuelve 422 (Error de Negocio)
- **GIVEN** un cuerpo de petición con acción "reprogramar_invalido"
- **WHEN** la API valida el esquema de entrada
- **THEN** la respuesta es `422` con código de error "VALIDACION"

