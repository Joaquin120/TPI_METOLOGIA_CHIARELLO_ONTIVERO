# Tasks

## 1. Dominio y Migraciones de Base de Datos

- [x] 1.1 Crear migración SQLite `backend/src/infrastructure/migrations/006_bloqueos.sql` con tabla `bloqueo_sillon` e índices compuestos, y registrarla en `backend/src/infrastructure/database.py`; verificar ejecutando `migrar()` en tests de esquema.
- [x] 1.2 Definir modelo inmutable `BloqueoSillon` en `backend/src/domain/models.py` y excepciones puras `SillonBloqueadoError`, `ConflictoTurnosExistentesError`, `BloqueoSolapadoError`, `BloqueoNoEncontradoError` en `backend/src/domain/exceptions.py`; verificar pureza de dominio ejecutando `pytest backend/tests/test_pureza_dominio.py`.
- [x] 1.3 Definir interfaz abstracta `PuertoBloqueos` en `backend/src/domain/puertos.py` con métodos `guardar`, `buscar_bloqueos_solapados`, `listar`, `obtener_por_id` y `eliminar`; verificar consistencia de tipos.

## 2. Repositorio de Persistencia SQLite

- [x] 2.1 Implementar `RepositorioBloqueosSqlite` en `backend/src/repositories/bloqueos_sqlite.py` con operaciones CRUD y búsqueda de intervalos semiabiertos `[inicio, fin)` acotadas a `tenant_id`; verificar con nueva suite `backend/tests/test_bloqueos_repositorio.py`.
- [x] 2.2 Validar persistencia de bloqueos contiguos en el límite exacto y rechazo de solapamientos entre bloqueos; verificar con casos de borde en `backend/tests/test_bloqueos_repositorio.py`.

## 3. Integración en Dominio de Turnos

- [x] 3.1 Integrar `PuertoBloqueos` en `ServicioTurnos.agendar` para rechazar altas de turnos en sillones bloqueados con `SillonBloqueadoError`; verificar con pruebas unitarias en `backend/tests/test_bloqueos_dominio.py`.
- [x] 3.2 Integrar `PuertoBloqueos` en `ServicioTurnos.reprogramar` para rechazar reprogramaciones hacia sillones bloqueados con `SillonBloqueadoError`; verificar con pruebas unitarias en `backend/tests/test_bloqueos_dominio.py`.
- [x] 3.3 Implementar validación de salvaguarda RP-07 al registrar bloqueos, impidiendo bloquear sillones que tengan turnos activos (`PENDIENTE`/`CONFIRMADO`) con `ConflictoTurnosExistentesError`; verificar en `backend/tests/test_bloqueos_dominio.py`.

## 4. Capa API REST, RBAC y Auditoría

- [x] 4.1 Definir esquemas Pydantic `BloqueoCrear` y `BloqueoRespuesta` en `backend/src/api/esquemas.py` y mapear excepciones a HTTP 404 (`BLOQUEO_NO_ENCONTRADO`) y 409 (`SILLON_BLOQUEADO`, `CONFLICTO_TURNOS_EXISTENTES`, `BLOQUEO_SOLAPADO`) en `backend/src/api/errores.py`; verificar mapeo y envelope estándar.
- [x] 4.2 Implementar router `backend/src/api/routers/bloqueos.py` con endpoints `POST /api/v1/bloqueos`, `GET /api/v1/bloqueos` y `DELETE /api/v1/bloqueos/{id}`, aplicando RBAC (`Administrador` para crear/eliminar, `Recepcionista`/`Administrador` para listar) y bitácora de auditoría inmutable; verificar con suite de integración `backend/tests/test_api_bloqueos.py`.
- [x] 4.3 Registrar router en `backend/src/api/app.py`, actualizar dependencias en `backend/src/api/dependencias.py` y verificar que la suite completa del backend pase al 100% verde sin regresiones con `python3.12 -m pytest backend/tests --cov=src`.
