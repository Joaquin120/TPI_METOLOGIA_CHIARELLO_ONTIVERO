# Proposal

## Why

La dirección y administración de un centro odontológico necesita supervisar el rendimiento y la operatividad de la clínica: el volumen total de turnos, su distribución por estado (`PENDIENTE`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`), la tasa porcentual de cancelaciones y la utilización operativa de profesionales y sillones/boxes.

Actualmente, el sistema gestiona de forma transaccional turnos, recursos y pacientes (C-01 a C-07), pero carece de endpoints analíticos y reportes agregados que consoliden estas métricas por clínica. Este cambio introduce la capacidad `reportes-metricas` (Change `c-08-reportes-metricas`), proveyendo endpoints analíticos protegidos por autenticación JWT y control de roles RBAC, garantizando aislamiento multi-tenant estricto y total apego a la política de privacidad y datos sintéticos (RN-06).

## What Changes

- **Capa de Persistencia y Consultas Agregadas**:
  - Implementación de consultas analíticas y métodos de cálculo métrico acotados incondicionalmente a `tenant_id` y con filtros opcionales de rango temporal (`fecha_desde`, `fecha_hasta`).
  - Cálculo de KPIs: total de turnos, distribución por estado, tasa porcentual de cancelación (`(cancelados / total) * 100`), distribución de turnos por profesional y distribución por sillón.
- **Capa API REST y Esquemas Pydantic**:
  - Nuevos esquemas en `backend/src/api/esquemas.py`:
    - `MetricasTurnosRespuesta`: Total de turnos, conteo detallado por estado (`pendientes`, `confirmados`, `cancelados`, `completados`) y tasa de cancelación.
    - `MetricasRecursosRespuesta`: Lista de métricas agregadas por profesional y por sillón/box dentro del tenant.
    - `MetricasFiltro`: Parámetros de query para filtrado por fecha (`fecha_desde`, `fecha_hasta` en formato `YYYY-MM-DD`).
  - Nuevo router `backend/src/api/routers/metricas.py` exponiendo:
    - `GET /api/v1/metricas/turnos`: Resumen agregado de métricas de turnos del tenant (código HTTP 200).
    - `GET /api/v1/metricas/recursos`: Resumen de carga y turnos por recurso clínico en el tenant (código HTTP 200).
- **Seguridad y Control de Acceso RBAC**:
  - Requiere token JWT válido (401 ante token ausente o inválido).
  - Acceso reservado para el rol `Administrador` (con acceso opcional de consulta para `Recepcionista`), rechazando roles no autorizados con código 403 (`ACCESO_DENEGADO`).
  - Aislamiento horizontal estricto: Las métricas jamás agregan datos de clínicas ajenas ni exponen indicadores cruzados entre tenants.
- **Envelope Uniforme de Errores**:
  - Todas las respuestas de error en los endpoints de métricas se unifican bajo `{"error": {"code": "...", "message": "..."}}`.
- **Datos Sintéticos y Privacidad (RN-06)**:
  - Los reportes consolidan indicadores numéricos sin exponer información personal identificable (PII) de pacientes, operando sobre fixtures sintéticos de prueba.

## Capabilities

### New Capabilities
- `reportes-metricas`: Consulta analítica de indicadores operativos y métricas de turnos y recursos clínicos (ocupación, estados y tasas de cancelación) acotada al tenant autenticado, con RBAC y envelope uniforme.

### Modified Capabilities
*(Ninguna. Las capacidades existentes `gestionar-pacientes`, `consultar-recursos`, `exponer-api-turnos`, `crear-turno`, `persistir-turnos`, `gestionar-estados-turno` y `autenticacion-autorizacion` conservan sus especificaciones normativas intactas).*

## Impact

- **Persistencia**: Nuevas consultas de agregación SQL sobre las tablas `turno`, `profesional` y `sillon` con filtro `WHERE tenant_id = ?`.
- **Capa API**:
  - Nuevos esquemas en `backend/src/api/esquemas.py`.
  - Nuevo router en `backend/src/api/routers/metricas.py`.
  - Registro del router en `create_app()` de `backend/src/api/app.py`.
  - Inyección de dependencias analíticas en `backend/src/api/dependencias.py`.
- **Tests**: Nueva suite de integración `backend/tests/test_api_metricas.py` con cobertura >= 97% y validación de aislamiento multi-tenant.
