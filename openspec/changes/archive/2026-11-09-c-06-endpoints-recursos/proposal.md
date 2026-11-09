# Proposal

## Why

Para programar y coordinar turnos odontológicos en el sistema (F-01, F-02), la recepción y los profesionales necesitan consultar el catálogo de recursos disponibles dentro de su clínica (tenant): los profesionales habilitados (con su matrícula y especialidad) y los sillones/boxes físicos (con su equipamiento y estado).

Actualmente, las entidades y tablas de `profesional` y `sillon` únicamente registran el nombre del recurso para el doble candado de turnos, y no existen endpoints HTTP para listarlos de forma acotada al tenant ni para verificar si están operativos (PA-01, RN-05). Este cambio expone los endpoints de consulta de recursos y amplía los modelos y el almacenamiento manteniendo aislamiento multi-tenant y datos puramente sintéticos (RN-06).

## What Changes

- **Evolución del esquema de base de datos**: Nueva migración `003_recursos.sql` que añade a `profesional` las columnas `matricula TEXT`, `especialidad TEXT` y `activo INTEGER NOT NULL DEFAULT 1`, y a `sillon` las columnas `equipamiento TEXT` y `activo INTEGER NOT NULL DEFAULT 1`.
- **Ampliación de entidades de dominio**: Extensión de `Profesional` (añadiendo `matricula`, `especialidad`, `activo`) y `Sillon` (añadiendo `equipamiento`, `activo`) con valores por defecto seguros para preservar retrocompatibilidad con la suite existente.
- **Acceso a datos multi-tenant**: Actualización de `RepositorioProfesionales` y `RepositorioSillones` para leer los nuevos atributos y soportar filtrado opcional `solo_activos: bool = True` (resolución MVP de PA-01).
- **Ampliación de semilla sintética**: Enriquecimiento de `infrastructure/seed.py` con matrículas ficticias, especialidades y equipamiento de ejemplo, además de casos con recursos inactivos para validación.
- **Nuevos endpoints REST autenticados**:
  - `GET /api/v1/profesionales`: Lista de profesionales del tenant autenticado con su matrícula, especialidad y estado activo. Soporta query parameter `solo_activos: bool = True`.
  - `GET /api/v1/sillones`: Lista de sillones del tenant autenticado con su equipamiento y estado activo. Soporta query parameter `solo_activos: bool = True`.
- **Seguridad y RBAC**:
  - Requiere autenticación JWT Bearer válida (401 ante token ausente, expirado o inválido).
  - Acceso permitido a los roles del tenant (`Administrador`, `Recepcionista`, `Profesional`).
  - Filtrado estricto por `tenant_id` derivado del token JWT (`ContextoUsuario`), impidiendo fugas de recursos entre clínicas.

## Capabilities

### New Capabilities
- `consultar-recursos`: Consulta de catálogo de recursos clínicos (profesionales y sillones/boxes) acotada al tenant autenticado, con atributos operativos y filtro por disponibilidad/estado activo.

### Modified Capabilities
*(Ninguna. Las capacidades de `exponer-api-turnos`, `crear-turno`, `persistir-turnos`, `gestionar-estados-turno` y `autenticacion-autorizacion` conservan sus requisitos normativos intactos).*

## Impact

- **Base de datos**: Nueva migración `backend/src/infrastructure/migrations/003_recursos.sql`.
- **Modelos de dominio**: `backend/src/domain/models.py` (`Profesional`, `Sillon`).
- **Persistencia**: `backend/src/repositories/recursos.py` (`RepositorioProfesionales`, `RepositorioSillones`).
- **Semilla**: `backend/src/infrastructure/seed.py`.
- **Capa API**:
  - Nuevos esquemas en `backend/src/api/esquemas.py` (`ProfesionalRespuesta`, `SillonRespuesta`).
  - Nuevo router `backend/src/api/routers/recursos.py`.
  - Registro del router en `backend/src/api/app.py`.
- **Compatibilidad**: 100% retrocompatible con los 155 tests existentes de turnos, auth y dominio.

