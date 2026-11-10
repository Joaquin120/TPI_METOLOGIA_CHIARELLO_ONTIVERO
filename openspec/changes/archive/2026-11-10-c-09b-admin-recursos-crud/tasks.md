# Tasks

## 1. Dominio y Adaptadores de Persistencia

- [x] 1.1 Declarar `RecursoDuplicadoError` en `backend/src/domain/exceptions.py` preservando la pureza del dominio (0 dependencias externas) y verificando con `test_pureza_dominio.py`.
- [x] 1.2 Implementar métodos `crear(nombre, matricula, especialidad, activo)` y `actualizar(id_, nombre, matricula, especialidad, activo)` en `RepositorioProfesionales` (`backend/src/repositories/recursos.py`) con control de duplicidad por tenant y retorno de `None` si el ID no pertenece al tenant.
- [x] 1.3 Implementar métodos `crear(nombre, equipamiento, activo)` y `actualizar(id_, nombre, equipamiento, activo)` en `RepositorioSillones` (`backend/src/repositories/recursos.py`) con control de duplicidad por tenant y retorno de `None` si el ID no pertenece al tenant.
- [x] 1.4 Implementar pruebas de persistencia en `backend/tests/test_recursos_repositorio_crud.py` comprobando en SQLite real la creación, actualización, colisiones de unicidad y aislamiento multi-tenant estricto.

## 2. Esquemas Pydantic y Capa API REST

- [x] 2.1 Definir los esquemas `ProfesionalCrear`, `ProfesionalActualizar`, `SillonCrear` y `SillonActualizar` en `backend/src/api/esquemas.py` con `extra="forbid"` y validación de texto no vacío.
- [x] 2.2 Declarar las excepciones HTTP y códigos de error `ErrorProfesionalNoEncontrado` (404), `ErrorSillonNoEncontrado` (404), `ErrorNombreProfesionalDuplicado` (409) y `ErrorNombreSillonDuplicado` (409) en `backend/src/api/errores.py`.
- [x] 2.3 Implementar los endpoints `POST /api/v1/profesionales`, `PUT /api/v1/profesionales/{id}`, `POST /api/v1/sillones` y `PUT /api/v1/sillones/{id}` en `backend/src/api/routers/recursos.py`, restringiendo el acceso con RBAC exclusivo al rol `Administrador` mediante `ContextoUsuario`.
- [x] 2.4 Integrar el registro de eventos en la bitácora de auditoría (`CREAR_PROFESIONAL`, `MODIFICAR_PROFESIONAL`, `CREAR_SILLON`, `MODIFICAR_SILLON`) utilizando `RepositorioAuditoriaSqlite` (C-09).

## 3. Pruebas de Integración y Verificación Global

- [x] 3.1 Implementar la suite `backend/tests/test_api_admin_recursos.py` cubriendo exhaustivamente todos los escenarios Given/When/Then: altas y modificaciones exitosas (201/200), duplicidad de nombres (409), recursos inexistentes o ajenos al tenant (404), RBAC (403 para recepcionista y profesional), sin token (401), validación (422) y verificación de registros de auditoría.
- [x] 3.2 Verificar en prueba de integración que un profesional o sillón creado mediante la API puede ser utilizado de inmediato para agendar o reprogramar turnos en el tenant.
- [x] 3.3 Ejecutar la suite completa con `python3.12 -m pytest backend/tests` y verificar 100% de tests passing con cobertura >= 97% y pureza de dominio intacta.
