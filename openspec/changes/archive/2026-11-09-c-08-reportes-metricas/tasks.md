# Tasks

## 1. Persistencia y consultas analíticas de métricas

- [x] 1.1 Implementar `RepositorioMetricasSqlite` en `backend/src/repositories/metricas_sqlite.py` con métodos `obtener_metricas_turnos(tenant_id, fecha_desde=None, fecha_hasta=None)` y `obtener_metricas_recursos(tenant_id, fecha_desde=None, fecha_hasta=None)` acotados incondicionalmente por `tenant_id`.
- [x] 1.2 Implementar lógica de cálculo seguro de tasa de cancelación con manejo de división por cero (`total == 0 -> 0.0`) y redondeo a dos decimales.
- [x] 1.3 Verificar mediante pruebas de persistencia que las agregaciones SQL de `turno`, `profesional` y `sillon` operen correctamente sobre SQLite real sin cruces entre clínicas.

## 2. Esquemas Pydantic y control de validación

- [x] 2.1 Definir los esquemas `MetricasTurnosRespuesta`, `MetricaProfesionalItem`, `MetricaSillonItem` y `MetricasRecursosRespuesta` en `backend/src/api/esquemas.py`.
- [x] 2.2 Incorporar validaciones de rango de fechas (`fecha_desde <= fecha_hasta`) con respuesta de error 422 bajo el envelope unificado `{"error": {"code": "...", "message": "..."}}`.

## 3. Router API y endpoints de métricas

- [x] 3.1 Implementar el router `backend/src/api/routers/metricas.py` con los endpoints `GET /api/v1/metricas/turnos` y `GET /api/v1/metricas/recursos`, requiriendo autenticación Bearer JWT y control de acceso RBAC para roles `Administrador` y `Recepcionista`.
- [x] 3.2 Configurar la dependencia `obtener_repositorio_metricas` en `backend/src/api/dependencias.py` y registrar el router `metricas.router` en `create_app()` de `backend/src/api/app.py`.

## 4. Suite de pruebas de integración y verificación

- [x] 4.1 Implementar la suite `backend/tests/test_api_metricas.py` con fixtures y datos puramente sintéticos (RN-06), cubriendo:
  - Consulta general de métricas de turnos (200).
  - Filtrado por rango de fechas (200) y validación de fechas invertidas (422).
  - Cálculo de tasa de cancelación (0 turnos -> 0.0%, 10 turnos con 2 cancelados -> 20.0%).
  - Aislamiento multi-tenant estricto (datos del tenant B invisibles en métricas del tenant A).
  - Consulta de métricas de recursos clínicos (turnos por profesional y por sillón) (200).
  - Control de acceso RBAC: éxito con `Administrador` y `Recepcionista`, rechazo con `Profesional` (403 `ACCESO_DENEGADO`), rechazo sin autenticación (401 `NO_AUTENTICADO`).
  - Envelope uniforme de errores en respuestas 401, 403 y 422.
- [x] 4.2 Ejecutar la suite completa de tests con `python3.12 -m pytest backend/tests` y verificar 100% de tests en verde con cobertura >= 97% en los nuevos módulos.
