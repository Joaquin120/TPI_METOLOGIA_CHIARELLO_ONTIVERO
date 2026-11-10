# Design

## Context

El sistema turnos-odontologia cuenta actualmente con persistencia en SQLite, arquitectura hexagonal desacoplada, autenticación JWT con control de roles RBAC, catálogo de recursos clínicos y gestión de pacientes (C-01 a C-07). Sin embargo, el equipo de administración y recepción carece de una vista consolidada sobre el volumen operativo de turnos, la tasa de cancelación y la carga de trabajo asignada a profesionales y sillones/boxes.

Ver `proposal.md` para la motivación y alcance general de este cambio. Para los requisitos normativos y escenarios Given/When/Then, consultar `specs/reportes-metricas/spec.md`.

## Goals / Non-Goals

**Goals:**
- Exponer los endpoints REST analíticos de solo lectura `GET /api/v1/metricas/turnos` y `GET /api/v1/metricas/recursos` protegidos por autenticación Bearer JWT y control de roles RBAC.
- Implementar el adaptador de persistencia analítica `RepositorioMetricasSqlite` en `backend/src/repositories/metricas_sqlite.py`, ejecutando agregaciones SQL optimizadas (`COUNT`, `GROUP BY`) con filtro incondicional por `tenant_id`.
- Calcular indicadores clave de rendimiento (KPIs): total de turnos, conteo desglosado por estado (`PENDIENTE`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`), tasa porcentual de cancelaciones (`(cancelados / total) * 100.0`), turnos por profesional y turnos por sillón.
- Proveer soporte para filtrado por rango temporal opcional (`fecha_desde` y `fecha_hasta` en formato `YYYY-MM-DD`).
- Restringir el acceso exclusivamente a los roles `Administrador` y `Recepcionista`, denegando el acceso a otros roles con código HTTP 403 (`ACCESO_DENEGADO`) y a peticiones no autenticadas con código HTTP 401 (`NO_AUTENTICADO`).
- Preservar el envelope uniforme de errores `{"error": {"code": "...", "message": "..."}}` ante errores de validación de parámetros (422), autenticación (401) y permisos (403).
- Implementar la suite de pruebas `backend/tests/test_api_metricas.py` con datos puramente sintéticos (RN-06), asegurando una cobertura >= 97% y el 100% de la suite verde.

**Non-Goals:**
- Reportes financieros, facturación o costos de tratamientos (fuera del alcance del MVP).
- Exportación asíncrona a archivos PDF, Excel o CSV (diferido para evolutivos posteriores).
- Modificación del ciclo de vida o máquina de estados de los turnos (las métricas son estrictamente de solo lectura).
- Creación de nuevas tablas relacionales (las métricas agregan sobre las tablas existentes `turno`, `profesional` y `sillon`).

## Decisions

### D1: Repositorio analítico especializado `RepositorioMetricasSqlite`
- **Decisión**: Implementar las consultas analíticas en una clase dedicada `RepositorioMetricasSqlite` en `backend/src/repositories/metricas_sqlite.py`, en lugar de sobrecargar los repositorios transaccionales existentes (`RepositorioTurnosSqlite`, `RepositorioRecursosSqlite`).
- **Razón**: Respeta el principio de responsabilidad única (SRP) y separación entre lectura transaccional y analítica (CQRS liviano). Las consultas de métricas requieren agregaciones SQL (`COUNT`, `GROUP BY`) directas sobre la base, evitando cargar entidades completas en memoria para luego calcular métricas en Python.
- **Alternativa descartada**: Cargar todos los modelos `Turno` en memoria y hacer agregaciones con listas de Python, lo cual degradaría la memoria y el rendimiento a medida que crece el histórico.

### D2: Cálculo seguro de la tasa de cancelación y casos de borde
- **Decisión**: La tasa de cancelación se define como `(cancelados / total) * 100.0` redondeada a dos decimales. Si `total == 0`, la tasa de cancelación es exactamente `0.0`.
- **Razón**: Previene excepciones por división por cero (`ZeroDivisionError`) cuando una clínica recién creada o un rango de fechas no posee turnos registrados.
- **Alternativa descartada**: Retornar `null` o lanzar un error 404 cuando no hay turnos; la ausencia de turnos es un estado operacional válido que debe reflejar totales en 0 y tasa en 0.0%.

### D3: Filtrado temporal inclusivo y validación de rango
- **Decisión**: Los filtros opcionales de fecha `fecha_desde` y `fecha_hasta` aceptan formato ISO `YYYY-MM-DD`. El filtro sobre la columna `inicio` se aplica considerando:
  - `fecha_desde`: `inicio >= fecha_desde || 'T00:00:00'`
  - `fecha_hasta`: `inicio <= fecha_hasta || 'T23:59:59'`
  Si `fecha_desde > fecha_hasta`, se rechaza con código HTTP 422 y código de error `RANGO_FECHAS_INVALIDO`.
- **Razón**: Permite consultas analíticas precisas sobre períodos específicos (diario, semanal, mensual) sin ambigüedades horarias.
- **Alternativa descartada**: Usar marcas de tiempo Unix numéricas que dificultan la auditoría e inspección en HTTP.

### D4: Política RBAC y roles permitidos
- **Decisión**: Los endpoints de métricas requieren token Bearer JWT con roles autorizados: `Administrador` y `Recepcionista`.
  - Roles como `Profesional` son rechazados con HTTP 403 `{"error": {"code": "ACCESO_DENEGADO", "message": "Rol no autorizado para consultar metricas"}}`.
  - Peticiones sin token o con token inválido reciben HTTP 401 `NO_AUTENTICADO` / `TOKEN_INVALIDO`.
- **Razón**: Las métricas consolidadas de la clínica son de interés directivo y administrativo. Un profesional no debe tener acceso a las métricas agregadas globales ni a la carga de sus colegas.
- **Alternativa descartada**: Permitir acceso irrestricto a cualquier usuario autenticado.

### D5: Aislamiento multi-tenant estricto (Regla Dura 8)
- **Decisión**: Todas las consultas SQL agregan incondicionalmente la cláusula `WHERE tenant_id = ?` derivada exclusivamente del token JWT autenticado (nunca de parámetros de URL o payloads del cliente). En métricas de recursos, los `LEFT JOIN` a turnos también se restringen por el `tenant_id` de la clínica.
- **Razón**: Garantiza hermeticidad absoluta de datos e indicadores entre clínicas diferentes.
- **Alternativa descartada**: Permitir pasar `tenant_id` por query param para administradores globales.

### D6: Esquemas Pydantic y tipado estricto
- **Decisión**: En `backend/src/api/esquemas.py` se definen:
  - `MetricasTurnosRespuesta`: `total: int`, `por_estado: dict[str, int]`, `tasa_cancelacion: float`, `fecha_desde: str | None`, `fecha_hasta: str | None`.
  - `MetricaProfesionalItem`: `profesional_id: int`, `nombre: str`, `total_turnos: int`.
  - `MetricaSillonItem`: `sillon_id: int`, `nombre: str`, `total_turnos: int`.
  - `MetricasRecursosRespuesta`: `profesionales: list[MetricaProfesionalItem]`, `sillones: list[MetricaSillonItem]`, `fecha_desde: str | None`, `fecha_hasta: str | None`.
- **Razón**: Proporciona contratos REST tipados, serialización automática y documentación OpenAPI clara.

## Risks / Trade-offs

- **[Riesgo: División por cero cuando no existen turnos en el período]** → *Mitigación:* Se evalúa si el denominador `total` es cero, retornando `0.0` para `tasa_cancelacion`.
- **[Riesgo: Fuga de información entre tenants en métricas de recursos]** → *Mitigación:* Se valida que tanto profesionales, sillones como turnos filtrados pertenezcan estrictamente al `tenant_id` del usuario autenticado.
- **[Riesgo: Parámetros de fecha mal formados]** → *Mitigación:* Validación mediante Pydantic y parseo con envelope uniforme ante errores 422.

## Migration Plan

No se requieren migraciones relacionales para este change, ya que opera de forma agregada sobre las tablas existentes (`turno`, `profesional`, `sillon`).
