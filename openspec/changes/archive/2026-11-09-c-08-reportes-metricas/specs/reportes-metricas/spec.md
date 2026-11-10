# Spec Delta

## Purpose

Permite consultar métricas e indicadores operativos de la agenda odontológica (estados de turnos, tasa de cancelación y utilización de recursos) dentro del tenant autenticado, garantizando aislamiento multi-tenant y control de acceso.

## ADDED Requirements

### Requirement: Consulta de métricas agregadas de turnos
El sistema SHALL exponer un endpoint `GET /api/v1/metricas/turnos` que devuelva métricas consolidadas de los turnos pertenecientes al tenant del usuario autenticado, incluyendo total de turnos, conteo por estado (`PENDIENTE`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`) y tasa de cancelación porcentual.

#### Scenario: Consulta exitosa de métricas generales de turnos
- **GIVEN** un usuario autenticado con rol `Administrador` en un tenant con turnos registrados en distintos estados
- **WHEN** envía una petición `GET /api/v1/metricas/turnos` sin filtros
- **THEN** el sistema responde con código HTTP 200 y un objeto JSON que detalla el total de turnos, el desglose por estado y la tasa de cancelación calculada

#### Scenario: Filtrado de métricas de turnos por rango de fechas
- **GIVEN** turnos registrados en diferentes fechas dentro del tenant
- **WHEN** el usuario envía `GET /api/v1/metricas/turnos?fecha_desde=2026-11-01&fecha_hasta=2026-11-15`
- **THEN** el sistema devuelve las métricas calculadas exclusivamente para los turnos contenidos en el rango de fechas indicado

#### Scenario: Cálculo exacto de la tasa de cancelación
- **GIVEN** un tenant con 10 turnos en total, de los cuales 2 están en estado `CANCELADO`
- **WHEN** el usuario consulta las métricas de turnos
- **THEN** la respuesta indica un total de 10 turnos y una tasa de cancelación del 20.0%

#### Scenario: Aislamiento estricto de métricas de turnos entre tenants
- **GIVEN** dos tenants con diferente volumen y distribución de turnos
- **WHEN** un usuario del tenant A consulta las métricas de turnos
- **THEN** el resultado refleja únicamente los turnos del tenant A y no se ve afectado por la actividad del tenant B

### Requirement: Consulta de métricas de recursos clínicos
El sistema SHALL exponer un endpoint `GET /api/v1/metricas/recursos` que devuelva la distribución y cantidad de turnos asignados por cada profesional y sillón/box del tenant autenticado.

#### Scenario: Consulta exitosa de métricas por recurso
- **GIVEN** un usuario autenticado perteneciente al tenant
- **WHEN** envía una petición `GET /api/v1/metricas/recursos`
- **THEN** el sistema responde con código HTTP 200 y una lista con los profesionales y sillones del tenant junto con la cantidad de turnos asociados a cada uno

#### Scenario: Aislamiento estricto de métricas de recursos entre tenants
- **GIVEN** recursos y turnos registrados en el tenant A y en el tenant B
- **WHEN** un usuario del tenant A consulta las métricas de recursos
- **THEN** la respuesta contiene únicamente profesionales y sillones pertenecientes al tenant A

### Requirement: Control de acceso a métricas por roles
El sistema SHALL restringir la consulta de métricas a roles con privilegios de gestión (`Administrador` y `Recepcionista`), denegando el acceso a otros roles o peticiones no autenticadas.

#### Scenario: Acceso permitido para administrador y recepcionista
- **GIVEN** un usuario autenticado con rol `Administrador` o `Recepcionista`
- **WHEN** consulta los endpoints de métricas
- **THEN** el sistema autoriza la operación y responde con código HTTP 200

#### Scenario: Rechazo de acceso para rol no autorizado
- **GIVEN** un usuario autenticado con un rol que no tiene permisos sobre métricas globales (ej. `Profesional` o externo)
- **WHEN** intenta acceder a `GET /api/v1/metricas/turnos`
- **THEN** el sistema deniega el acceso con código HTTP 403 y código de error `ACCESO_DENEGADO`

#### Scenario: Rechazo de peticiones sin autenticación
- **WHEN** un cliente invoca endpoints de métricas sin cabecera de autorización o con token inválido
- **THEN** el sistema rechaza la petición con código HTTP 401 y código de error `NO_AUTENTICADO` o `TOKEN_INVALIDO`

### Requirement: Envelope uniforme de errores
El sistema SHALL estructurar todas las respuestas de error en los endpoints de métricas bajo el envelope unificado `{"error": {"code": "...", "message": "..."}}`.

#### Scenario: Respuestas consistentes ante fallos de validación o acceso
- **WHEN** ocurre un error de validación de parámetros (422), falta de permisos (403) o autenticación (401)
- **THEN** la respuesta JSON contiene la clave `error` con sub-claves `code` y `message` de texto legible
