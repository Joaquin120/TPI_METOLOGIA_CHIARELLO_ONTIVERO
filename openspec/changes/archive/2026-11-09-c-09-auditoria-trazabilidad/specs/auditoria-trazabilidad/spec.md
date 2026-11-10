# Spec Delta

## Purpose

Permite consultar y registrar pistas de auditoría y trazabilidad inmutables sobre las operaciones realizadas en el sistema (acciones sobre turnos, pacientes, recursos y accesos) dentro del tenant autenticado, garantizando control de acceso restringido a administradores y hermeticidad multi-tenant.

## ADDED Requirements

### Requirement: Consulta de pistas de auditoría
El sistema SHALL exponer un endpoint `GET /api/v1/auditoria` que retorne la lista de registros de auditoría pertenecientes al tenant del usuario autenticado, ordenados cronológicamente de forma descendente, con soporte para filtrado opcional por fechas (`fecha_desde`, `fecha_hasta`), usuario (`usuario_id`), acción (`accion`) y entidad (`entidad`).

#### Scenario: Consulta exitosa del log de auditoría
- **GIVEN** un usuario autenticado con rol `Administrador` en un tenant con eventos registrados
- **WHEN** envía una petición `GET /api/v1/auditoria` sin parámetros de filtrado
- **THEN** el sistema responde con código HTTP 200 y una lista JSON de registros de auditoría que detallan id, usuario_id, accion, entidad, entidad_id, detalle y fecha_hora

#### Scenario: Filtrado de auditoría por rango de fechas
- **GIVEN** eventos de auditoría ocurridos en diferentes fechas
- **WHEN** el administrador consulta `GET /api/v1/auditoria?fecha_desde=2026-11-01&fecha_hasta=2026-11-08`
- **THEN** el sistema devuelve únicamente los registros comprendidos dentro de dicho intervalo temporal

#### Scenario: Filtrado de auditoría por entidad o acción
- **GIVEN** eventos registrados para diferentes entidades (`turno`, `paciente`) y acciones (`CREAR_TURNO`, `CREAR_PACIENTE`)
- **WHEN** el administrador consulta `GET /api/v1/auditoria?entidad=turno&accion=CREAR_TURNO`
- **THEN** el sistema devuelve únicamente los registros que coinciden exactamente con los criterios de filtrado

#### Scenario: Aislamiento estricto de auditoría entre tenants
- **GIVEN** eventos de auditoría registrados en el Tenant A y en el Tenant B
- **WHEN** el administrador del Tenant A consulta el log de auditoría
- **THEN** la respuesta contiene únicamente los registros del Tenant A y no expone ninguna actividad del Tenant B

### Requirement: Control de acceso a auditoría por roles
El sistema SHALL restringir la consulta de registros de auditoría de forma estricta y exclusiva al rol `Administrador`, rechazando cualquier otro rol o peticiones no autenticadas.

#### Scenario: Acceso permitido para rol Administrador
- **GIVEN** un usuario autenticado con rol `Administrador`
- **WHEN** envía una petición `GET /api/v1/auditoria`
- **THEN** el sistema autoriza la operación y responde con código HTTP 200

#### Scenario: Rechazo de acceso para otros roles
- **GIVEN** un usuario autenticado con rol `Recepcionista` o `Profesional`
- **WHEN** intenta acceder a `GET /api/v1/auditoria`
- **THEN** el sistema deniega el acceso con código HTTP 403 y código de error `ACCESO_DENEGADO`

#### Scenario: Rechazo de peticiones sin autenticación
- **WHEN** un cliente invoca `GET /api/v1/auditoria` sin token Bearer o con token corrupto
- **THEN** el sistema rechaza la petición con código HTTP 401 y código de error `NO_AUTENTICADO` o `TOKEN_INVALIDO`

### Requirement: Persistencia e inmutabilidad de eventos de auditoría
El sistema SHALL proveer una tabla relacional `auditoria` en SQLite real para almacenar los eventos con trazabilidad estricta y claves foráneas hacia `tenant` y `usuario`.

#### Scenario: Registro persistente inmutable de evento
- **GIVEN** una base de datos con las migraciones aplicadas
- **WHEN** se invoca el registro de un evento de auditoría
- **THEN** la fila se almacena en SQLite con fecha_hora ISO, clave foránea al usuario y aislamiento por tenant_id

### Requirement: Envelope uniforme de errores
El sistema SHALL estructurar todas las respuestas de error en los endpoints de auditoría bajo el formato estándar `{"error": {"code": "...", "message": "..."}}`.

#### Scenario: Respuestas consistentes ante errores de autorización o validación
- **WHEN** se produce un error 401, 403 o 422 en el endpoint de auditoría
- **THEN** el cuerpo JSON contiene la clave `error` con sub-claves `code` y `message`
