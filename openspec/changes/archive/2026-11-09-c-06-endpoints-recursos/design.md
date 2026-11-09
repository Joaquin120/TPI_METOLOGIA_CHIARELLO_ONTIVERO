# Design

## Context

El sistema cuenta con un motor de turnos desacoplado con persistencia SQLite y autenticación JWT con control de roles (C-01 a C-05). En `src/repositories/recursos.py`, las clases `RepositorioProfesionales` y `RepositorioSillones` únicamente gestionaban `id` y `nombre` para el doble candado de turnos, y no existían rutas HTTP ni filtros de disponibilidad para consultar el catálogo de recursos.

Para permitir a los actores de la clínica seleccionar profesionales habilitados y sillones operativos al agendar turnos (F-04, F-05), este cambio provee la evolución de esquema, modelos de dominio, repositorios multi-tenant y endpoints REST correspondientes.

## UI Mockups

Decision: no (no UI)

## Goals / Non-Goals

**Goals:**
- Exponer `GET /api/v1/profesionales` y `GET /api/v1/sillones` acotados al tenant autenticado vía JWT.
- Extender las tablas `profesional` y `sillon` con atributos operativos (`matricula`, `especialidad`, `equipamiento`, `activo`) mediante una nueva migración idempotente.
- Preservar retrocompatibilidad total en las clases de dominio `Profesional` y `Sillon` mediante defaults seguros.
- Soportar filtrado por disponibilidad operativa (`solo_activos: bool = True`) resolviendo el criterio MVP de PA-01.
- Ampliar la semilla sintética con recursos completos y casos inactivos para pruebas (RN-06).

**Non-Goals:**
- Endpoints de alta/modificación/baja de recursos (CRUD de administración de recursos corresponde a `C-09 admin-recursos-crud`).
- Bloqueo de sillones por mantenimiento temporal (corresponde a `C-10 bloqueo-sillon` / PA-15).
- Modificar el comportamiento de `GET /api/v1/turnos` o `POST /api/v1/turnos`.

## Decisions

### D1: Migración incremental `003_recursos.sql`
- **Decisión**: Crear `backend/src/infrastructure/migrations/003_recursos.sql` con instrucciones `ALTER TABLE profesional ADD COLUMN ...` y `ALTER TABLE sillon ADD COLUMN ...`.
- **Razón**: El runner `migrar(conexion)` aplica archivos `.sql` en orden y registra su ejecución en `schema_migrations`. Esto no altera bases de datos existentes y preserva el principio de migraciones inmutables.
- **Alternativa descartada**: Modificar `001_init.sql` directamente, lo que invalidaría bases ya creadas e impediría trazabilidad de cambios en producción/desarrollo.

### D2: Retrocompatibilidad en entidades de dominio
- **Decisión**: Extender `Profesional` y `Sillon` en `src/domain/models.py` usando `dataclass(frozen=True)` con campos opcionales con valores por defecto:
  ```python
  @dataclass(frozen=True)
  class Profesional:
      nombre: str
      id: int | None = None
      matricula: str | None = None
      especialidad: str | None = None
      activo: bool = True

  @dataclass(frozen=True)
  class Sillon:
      nombre: str
      id: int | None = None
      equipamiento: str | None = None
      activo: bool = True
  ```
- **Razón**: Permite representar el catálogo completo de recursos sin alterar la firma posicional de `Profesional(nombre, id)` utilizada en `ServicioTurnos` y en los 155 tests existentes.
- **Alternativa descartada**: Crear clases separadas (e.g. `ProfesionalDetalle`), lo cual duplicaría tipos y violaría la cohesión del dominio.

### D3: Filtrado por disponibilidad activa (resolución MVP de PA-01)
- **Decisión**: Añadir el parámetro query `solo_activos: bool = True` en `GET /api/v1/profesionales` y `GET /api/v1/sillones`.
  - Cuando es `True` (por defecto): la consulta SQL filtra `WHERE tenant_id = ? AND activo = 1`.
  - Cuando es `False`: la consulta omite el filtro de activo y devuelve todos los recursos del tenant.
- **Razón**: Al crear turnos, la interfaz de recepción requiere ver únicamente los profesionales y sillones activos para evitar programaciones erróneas. Al mismo tiempo, permite a la administración auditar recursos inactivos.
- **Alternativa descartada**: Excluir permanentemente recursos inactivos en el backend sin opción de consulta.

### D4: Router desacoplado y esquemas Pydantic
- **Decisión**: Crear `src/api/routers/recursos.py` e incluirlo en `create_app()` con prefijo `/api/v1`.
  - Modelos de respuesta: `ProfesionalRespuesta` (`id`, `nombre`, `matricula`, `especialidad`, `activo`) y `SillonRespuesta` (`id`, `nombre`, `equipamiento`, `activo`).
  - El `tenant_id` se extrae de la dependencia `obtener_usuario_actual` (`ContextoUsuario.tenant_id`), jamás de un parámetro libre en query o body.
  - Roles permitidos: `Administrador`, `Recepcionista`, `Profesional` (todos tienen lectura de catálogo).

### D5: Semilla sintética ampliada (RN-06)
- **Decisión**: En `src/infrastructure/seed.py`, parametrizar la siembra para insertar profesionales con matrícula sintética ("MP-1001", "MP-1002"), especialidades ("Odontología General", "Ortodoncia"), sillones ("Sillón 1", "Sillón 2") con equipamiento ("Básico", "Completo con Rayos X"), y recursos inactivos de prueba ("Dr. Inactivo", "Sillón 3 - Mantenimiento").
- **Razón**: Proporciona datos realistas pero ficticios para verificar los escenarios de filtrado y cumplir la regla dura de datos sintéticos.

## Risks / Trade-offs

- **[Riesgo] sqlite3 no soporta múltiples ALTER TABLE en una sola sentencia**:
  → *Mitigación*: En `003_recursos.sql`, ejecutar cada `ALTER TABLE` como sentencia individual separada por `;`.
- **[Riesgo] Desincronización en consultas existentes de `RepositorioProfesionales`**:
  → *Mitigación*: Métodos existentes como `resolver_id()` y `obtener_por_id()` se actualizan para mapear las nuevas columnas sin romper su firma ni valor de retorno.
- **[Riesgo] Fuga inter-tenant en catálogo**:
  → *Mitigación*: Todas las consultas SQL en `RepositorioProfesionales` y `RepositorioSillones` contienen forzosamente `tenant_id = ?` obtenido desde el token autenticado. Tests automatizados validan el aislamiento estricto.

## Migration Plan

1. La migración `003_recursos.sql` se ejecuta automáticamente en el arranque de la factoría `create_app()` mediante `migrar(conexion)`.
2. Las tablas existentes conservan sus filas previas; las nuevas columnas toman el default `activo = 1` y `NULL` para matrícula, especialidad y equipamiento.
3. La semilla sintética `sembrar_datos_iniciales()` actualiza o complementa los registros sintéticos por defecto.

