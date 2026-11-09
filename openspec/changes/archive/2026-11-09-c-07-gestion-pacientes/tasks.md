# Tasks

## 1. Esquema de persistencia y modelos de dominio

- [x] 1.1 Crear migración `backend/src/infrastructure/migrations/004_pacientes.sql` añadiendo columna `telefono TEXT` e índice compuesto `UNIQUE(tenant_id, dni)` a la tabla `paciente`; verificar su aplicación idempotente mediante `migrar(conexion)`.
- [x] 1.2 Extender la entidad `Paciente` en `backend/src/domain/models.py` como `dataclass(frozen=True)` con campos `dni: str`, `nombre: str`, `telefono: str`, `tenant_id: int` e `id: int | None = None`; verificar que los tests existentes y los guard tests de pureza (`test_pureza_dominio.py`) permanezcan en verde.

## 2. Repositorio de persistencia y semilla sintética

- [x] 2.1 Implementar `RepositorioPacientesSqlite` en `backend/src/repositories/pacientes_sqlite.py` con métodos `crear`, `buscar_por_id`, `buscar_por_dni` y `listar` acotados incondicionalmente a `tenant_id`; verificar con pruebas unitarias sobre base SQLite real.
- [x] 2.2 Ampliar `sembrar_datos_iniciales()` en `backend/src/infrastructure/seed.py` con pacientes sintéticos de prueba conformes a RN-06; verificar idempotencia de la semilla.

## 3. Capa API y endpoints REST de pacientes

- [x] 3.1 Definir esquemas Pydantic `PacienteCrear`, `PacienteRespuesta` y `PacienteFiltro` en `backend/src/api/esquemas.py` con validación regex para DNI de 8 dígitos (`^\d{8}$`), teléfono y `extra="forbid"`; verificar validaciones con tests unitarios.
- [x] 3.2 Incorporar `ErrorPacienteDuplicado` y handler para HTTP 409 con envelope `{"error": {"code": "PACIENTE_DUPLICADO", "message": "..."}}` en `backend/src/api/errores.py`; verificar respuestas uniformes.
- [x] 3.3 Implementar router `backend/src/api/routers/pacientes.py` exponiendo `POST /api/v1/pacientes` y `GET /api/v1/pacientes` protegidos por autenticación JWT y control RBAC (`ContextoUsuario`), y registrarlo en `create_app()` de `backend/src/api/app.py`.

## 4. Suite de pruebas, auditoría sintética y cobertura

- [x] 4.1 Implementar la suite `backend/tests/test_api_pacientes.py` guiada por `.atl/skills/generador-datos-pacientes-sinteticos.md`, cubriendo escenarios Given/When/Then de alta exitosa (201), duplicados en mismo tenant (409), mismo DNI en distintos tenants (201), validación (422), RBAC (403/401) y aislamiento horizontal.
- [x] 4.2 Ejecutar la suite completa con `pytest` y verificar que el 100% de los tests pase con cobertura >= 97% sobre los módulos de pacientes.
- [x] 4.3 Auditar la suite y emitir el reporte formal con tabla de conformidad y dictamen final según el estándar de la skill de pacientes sintéticos.
