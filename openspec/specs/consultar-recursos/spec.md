# consultar-recursos Specification

## Purpose
Permite consultar el catálogo de recursos clínicos (profesionales odontólogos y sillones/boxes de atención) disponibles en el tenant autenticado, garantizando aislamiento multi-tenant y visibilidad de atributos operativos para la asignación de turnos.

## Requirements

### Requirement: Listado de profesionales por tenant
El sistema SHALL exponer un endpoint `GET /api/v1/profesionales` que devuelve los profesionales pertenecientes al tenant del usuario autenticado, incluyendo `id`, `nombre`, `matricula`, `especialidad` y `activo`.

#### Scenario: Listado exitoso de profesionales para usuario autenticado
- **GIVEN** un usuario autenticado con token JWT válido de un tenant con profesionales registrados
- **WHEN** envía una petición `GET /api/v1/profesionales`
- **THEN** el sistema responde con código HTTP 200 y una lista JSON de profesionales del tenant con sus atributos (`id`, `nombre`, `matricula`, `especialidad`, `activo`)

#### Scenario: Aislamiento estricto de profesionales entre tenants
- **GIVEN** dos tenants con profesionales propios registrados
- **WHEN** un usuario del tenant A consulta `GET /api/v1/profesionales`
- **THEN** la respuesta contiene únicamente los profesionales del tenant A y ningún registro del tenant B

#### Scenario: Filtrado opcional por profesionales activos
- **GIVEN** un tenant con profesionales en estado activo e inactivo
- **WHEN** el usuario consulta `GET /api/v1/profesionales?solo_activos=true`
- **THEN** la respuesta contiene únicamente profesionales con `activo=True`
- **WHEN** el usuario consulta `GET /api/v1/profesionales?solo_activos=false`
- **THEN** la respuesta incluye tanto profesionales activos como inactivos

#### Scenario: Rechazo de petición a profesionales sin autenticación
- **WHEN** un cliente envía `GET /api/v1/profesionales` sin cabecera `Authorization` o con token inválido
- **THEN** el sistema responde con código HTTP 401 y el envelope estándar `{"error": {"code": "...", "message": "..."}}`

### Requirement: Listado de sillones odontológicos por tenant
El sistema SHALL exponer un endpoint `GET /api/v1/sillones` que devuelve los sillones/boxes pertenecientes al tenant del usuario autenticado, incluyendo `id`, `nombre`, `equipamiento` y `activo`.

#### Scenario: Listado exitoso de sillones para usuario autenticado
- **GIVEN** un usuario autenticado con token JWT válido de un tenant con sillones registrados
- **WHEN** envía una petición `GET /api/v1/sillones`
- **THEN** el sistema responde con código HTTP 200 y una lista JSON de sillones del tenant con sus atributos (`id`, `nombre`, `equipamiento`, `activo`)

#### Scenario: Aislamiento estricto de sillones entre tenants
- **GIVEN** dos tenants con sillones propios registrados
- **WHEN** un usuario del tenant A consulta `GET /api/v1/sillones`
- **THEN** la respuesta contiene únicamente los sillones del tenant A y ningún registro del tenant B

#### Scenario: Filtrado opcional por sillones activos
- **GIVEN** un tenant con sillones en estado activo e inactivo
- **WHEN** el usuario consulta `GET /api/v1/sillones?solo_activos=true`
- **THEN** la respuesta contiene únicamente sillones con `activo=True`
- **WHEN** el usuario consulta `GET /api/v1/sillones?solo_activos=false`
- **THEN** la respuesta incluye tanto sillones activos como inactivos

#### Scenario: Rechazo de petición a sillones sin autenticación
- **WHEN** un cliente envía `GET /api/v1/sillones` sin cabecera `Authorization` o con token inválido
- **THEN** el sistema responde con código HTTP 401 y el envelope estándar `{"error": {"code": "...", "message": "..."}}`

### Requirement: Control de acceso a recursos por roles del tenant
El sistema SHALL permitir la consulta de profesionales y sillones a cualquier usuario autenticado del tenant (`Administrador`, `Recepcionista` o `Profesional`).

#### Scenario: Acceso concedido a roles válidos del tenant
- **GIVEN** un usuario autenticado con rol `Administrador`, `Recepcionista` o `Profesional`
- **WHEN** solicita `GET /api/v1/profesionales` o `GET /api/v1/sillones`
- **THEN** el sistema procesa la solicitud y devuelve código HTTP 200
