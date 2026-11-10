# Proposal

## Why

En la gestión diaria de una clínica u organización odontológica, la incorporación de nuevos odontólogos, la actualización de sus datos de matrícula o especialidad, la adición de sillones/boxes de atención y la modificación de su equipamiento o estado operativo (`activo`/`inactivo`) son responsabilidades exclusivas del rol Administrador (`actors.md` §2.1, `F-10`).

Actualmente, el sistema solo cuenta con endpoints de lectura de recursos (`GET /api/v1/profesionales` y `GET /api/v1/sillones` implementados en C-06), dependiendo de semillas estáticas o inserciones directas en base de datos para la existencia de profesionales y sillones.

Este cambio introduce la capacidad `administrar-recursos` (Change `c-09b-admin-recursos-crud`, correspondiente a `F-10`), habilitando al `Administrador` para dar de alta y editar profesionales y sillones mediante la API REST, garantizando la unicidad de nombres por tenant, validando atributos operativos, registrando cada operación en la bitácora inmutable de auditoría (C-09) y dejando los recursos operativos disponibles de inmediato para el agendamiento de turnos bajo estricto aislamiento multi-tenant (`RN-05`, `D-01`).

## What Changes

- **Capa de Persistencia y Repositorios (`src/repositories/recursos.py`)**:
  - Ampliación de `RepositorioProfesionales`:
    - Método `crear(nombre: str, matricula: str | None, especialidad: str | None, activo: bool = True) -> Profesional`: persiste el profesional en la tabla `profesional` acotado a `tenant_id`. Si ya existe un profesional con el mismo nombre en el tenant, rechaza la operación con `RecursoDuplicadoError`.
    - Método `actualizar(id_: int, nombre: str, matricula: str | None, especialidad: str | None, activo: bool) -> Profesional | None`: actualiza los campos de un profesional existente dentro del tenant. Retorna `None` si el id no existe en el tenant o lanza `RecursoDuplicadoError` si el nuevo nombre colisiona con otro profesional del mismo tenant.
  - Ampliación de `RepositorioSillones`:
    - Método `crear(nombre: str, equipamiento: str | None, activo: bool = True) -> Sillon`: persiste el sillón en la tabla `sillon` acotado a `tenant_id`. Si ya existe un sillón con el mismo nombre en el tenant, rechaza la operación con `RecursoDuplicadoError`.
    - Método `actualizar(id_: int, nombre: str, equipamiento: str | None, activo: bool) -> Sillon | None`: actualiza los campos de un sillón existente dentro del tenant. Retorna `None` si el id no existe en el tenant o lanza `RecursoDuplicadoError` si el nuevo nombre colisiona con otro sillón del mismo tenant.
- **Capa de Dominio y Excepciones (`src/domain/exceptions.py`)**:
  - Nueva excepción de dominio pura `RecursoDuplicadoError` para colisiones de unicidad dentro del tenant.
- **Capa API REST y Esquemas Pydantic (`src/api/esquemas.py`, `src/api/routers/recursos.py`)**:
  - Nuevos esquemas de entrada en `backend/src/api/esquemas.py`:
    - `ProfesionalCrear`: `nombre` (TextoRequerido), `matricula` (str | None), `especialidad` (str | None), `activo` (bool = True).
    - `ProfesionalActualizar`: `nombre` (TextoRequerido), `matricula` (str | None), `especialidad` (str | None), `activo` (bool).
    - `SillonCrear`: `nombre` (TextoRequerido), `equipamiento` (str | None), `activo` (bool = True).
    - `SillonActualizar`: `nombre` (TextoRequerido), `equipamiento` (str | None), `activo` (bool).
  - Nuevos endpoints en `backend/src/api/routers/recursos.py`:
    - `POST /api/v1/profesionales` (HTTP 201 Created) -> `ProfesionalRespuesta`
    - `PUT /api/v1/profesionales/{id}` (HTTP 200 OK) -> `ProfesionalRespuesta`
    - `POST /api/v1/sillones` (HTTP 201 Created) -> `SillonRespuesta`
    - `PUT /api/v1/sillones/{id}` (HTTP 200 OK) -> `SillonRespuesta`
- **Control de Acceso RBAC y Aislamiento Multi-Tenant**:
  - Acceso restringido exclusivamente al rol `Administrador` (`requerir_rol("Administrador")`).
  - Roles `Recepcionista` y `Profesional` reciben HTTP 403 `{"error": {"code": "ACCESO_DENEGADO", "message": "..."}}`.
  - Peticiones sin token reciben HTTP 401 `{"error": {"code": "NO_AUTENTICADO", ...}}`.
  - Intentos de modificar un recurso de otra clínica o inexistente devuelven HTTP 404 (`PROFESIONAL_NO_ENCONTRADO` / `SILLON_NO_ENCONTRADO`).
- **Trazabilidad y Auditoría (C-09)**:
  - Registro de eventos en la bitácora inmutable: `CREAR_PROFESIONAL`, `MODIFICAR_PROFESIONAL`, `CREAR_SILLON`, `MODIFICAR_SILLON`.
- **Integración con Turnos**:
  - Los recursos creados o actualizados en estado activo quedan disponibles de inmediato para asignar o reprogramar turnos en el tenant.

## Capabilities

### New Capabilities
- `administrar-recursos`: Creación y actualización administrativa de recursos clínicos (profesionales y sillones/boxes) con control de unicidad de nombres, RBAC exclusivo para Administrador, trazabilidad en bitácora de auditoría y disponibilidad para agendamiento multi-tenant.

### Modified Capabilities
*(Ninguna. Las capacidades existentes, incluida `consultar-recursos`, mantienen sus contratos normativos vigentes).*

## Impact

- **Persistencia**: Nuevos métodos `crear` y `actualizar` en `RepositorioProfesionales` y `RepositorioSillones`.
- **Dominio**: Nueva excepción `RecursoDuplicadoError` en `backend/src/domain/exceptions.py`.
- **Capa API**:
  - Nuevos esquemas en `backend/src/api/esquemas.py`.
  - Nuevos endpoints `POST`/`PUT` en `backend/src/api/routers/recursos.py`.
  - Mapeo de excepciones HTTP en `backend/src/api/errores.py`.
- **Tests**: Nueva suite de integración `backend/tests/test_api_admin_recursos.py` y pruebas de repositorio en `backend/tests/test_recursos_repositorio_crud.py`.
