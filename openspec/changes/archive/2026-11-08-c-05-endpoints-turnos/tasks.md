# Tasks

## 1. Dominio y Persistencia (Puertos y Repositorio SQLite)

- [x] 1.1 Extender `PuertoTurnos` y `ServicioTurnos` con métodos para búsqueda de turno por ID (`obtener_por_id`) y soporte de filtros opcionales en `listar` (`fecha`, `profesional_id`, `sillon_id`), y verificar con tests unitarios en `test_servicios.py` sin violar la pureza de dominio.
- [x] 1.2 Implementar en `RepositorioTurnosSqlite` la recuperación por identificador y tenant (`obtener_por_id`) y la construcción parametrizada de filtros en `listar(...)` con conjunción lógica (`AND`), y verificar con tests de integración en `test_repositorio_turnos_sqlite.py`.

## 2. Esquemas de Entrada y Manejo de Errores HTTP

- [x] 2.1 Definir en `src/api/esquemas.py` el modelo `TurnoCambioEstado` con validación estricta de la acción (`confirmar`, `cancelar`, `completar`), y registrar en `src/api/errores.py` la excepción `ErrorTurnoNoEncontrado` mapeada a `404` con código `TURNO_NO_ENCONTRADO`, verificando su comportamiento con tests unitarios.

## 3. Endpoints de Consulta y Filtrado (`GET /api/v1/turnos`)

- [x] 3.1 Actualizar `GET /api/v1/turnos` en `src/api/routers/turnos.py` para aceptar los query parameters opcionales `fecha`, `profesional_id` y `sillon_id`, validando formatos y delegando al repositorio dentro del tenant, y verificar con tests en `test_api_turnos.py`.
- [x] 3.2 Implementar la regla de aislamiento de agenda para el rol `Profesional` en `GET /api/v1/turnos`, garantizando que solo visualice sus propios turnos y denegando o restringiendo consultas hacia otros profesionales, y verificar con tests de roles en `test_rbac_tenancy.py`.

## 4. Endpoint de Cambio de Estado y Liberación de Recursos (`PATCH /api/v1/turnos/{id}/estado`)

- [x] 4.1 Implementar `PATCH /api/v1/turnos/{id}/estado` en `src/api/routers/turnos.py` restringido a roles `Recepcionista` y `Administrador`, resolviendo el turno por tenant, delegando la acción en `ServicioTurnos` y retornando `200` con el turno actualizado o `404` / `409` / `403` / `422`, y verificar con tests en `test_api_turnos.py`.
- [x] 4.2 Verificar la liberación inmediata de recursos (`RN-04`) tras una cancelación vía `PATCH`, comprobando que un agendamiento posterior (`POST /api/v1/turnos`) en el mismo intervalo para el mismo profesional y sillón resulte exitoso.

## 5. Verificación Integral y Suite de Regresión

- [x] 5.1 Ejecutar el guard test de pureza de dominio para certificar que `src/domain/` mantiene 0 imports de frameworks (`fastapi`, `pydantic`, `sqlite3`, `jwt`).
- [x] 5.2 Ejecutar la suite completa de pruebas en `backend/` con `pytest` asegurando el paso de todos los tests y una cobertura superior al 95%.

