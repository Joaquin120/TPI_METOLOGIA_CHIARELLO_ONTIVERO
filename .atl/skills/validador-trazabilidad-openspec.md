---
name: validador-trazabilidad-openspec
description: Audita y valida la trazabilidad técnica y metodológica Spec-Driven Development (SDD) para OpenSpec en cambios de backend y API. Verifica fidelidad normativa (escenarios spec.md vs pytest), pureza del dominio (cero acoplamiento en src/domain/), seguridad y aislamiento multi-tenant (tenant_id derivado de ContextoUsuario) y sincronización de artefactos (tasks.md, CHANGES.md y .active-orchestrator-state.json). Triggers: "validar trazabilidad", "auditoría SDD", "control de calidad openspec", "verificar fidelidad de spec", "auditar change", "revisar aislamiento", o antes de archivar un change.
---

# Validador de Trazabilidad OpenSpec (SDD)

Skill de auditoría técnica y trazabilidad **Spec-Driven Development (SDD)** para OpenSpec.
Valida formalmente que la implementación de un change sea fiel a los contratos especificados,
mantenga el aislamiento arquitectónico del dominio, garantice el aislamiento multi-tenant
y conserve la coherencia de estado entre los artefactos de planificación y el roadmap.

Es una **puerta de calidad y auditoría integral**, aplicable antes de archivar (`/opsx:archive`)
o tras completar la implementación de tareas (`/opsx:apply`).

## Cuándo invocarla

- Al finalizar la implementación de tareas de un change para verificar que no existan desvíos normativos.
- Antes de ejecutar `/opsx:archive` sobre cualquier change de backend o API.
- Al revisar PRs o cambios que involucren seguridad, autenticación, roles o modificaciones de contrato.
- Ante dudas sobre la pureza del paquete `src/domain/` o posibles fugas de `tenant_id`.

## Insumos a consultar ANTES de usarla

- `openspec/changes/<change-name>/specs/` → deltas normativos del change (`spec.md`).
- `openspec/changes/<change-name>/tasks.md` → checklist de tareas y verificación de progreso.
- `CHANGES.md` → estado general del change y dependencias en el roadmap.
- `.active-orchestrator-state.json` → estado operativo del orquestador y change activo.
- `backend/src/domain/` → código del núcleo de negocio a auditar por pureza.
- `backend/tests/` → suite de tests de integración y unitarios en pytest.

---

## 1. Dimensiones de Calidad y Reglas de Validación

### Dimensión 1 — Fidelidad Normativa (Contratos y Escenarios de Spec)

La implementación debe cubrir de forma estricta los requerimientos y escenarios definidos en los archivos `spec.md` asociados al change:

- **Mapeo exhaustivo de escenarios**: Cada bloque `#### Scenario:` presente en la spec debe contar con al menos una prueba automatizada en `backend/tests/` que verifique sus cláusulas **GIVEN / WHEN / THEN**.
- **Cobertura de códigos de estado HTTP**:
  - `200` / `201`: Respuestas exitosas para operaciones de consulta y creación autorizadas.
  - `401`: Rechazo por falta de credenciales (`NO_AUTENTICADO`), token expirado (`TOKEN_EXPIRADO`) o token inválido/corrupto (`TOKEN_INVALIDO`).
  - `403`: Rechazo cuando el usuario autenticado carece de permisos para la acción (`ACCESO_DENEGADO`).
  - `409`: Rechazo por conflictos de dominio (`SOLAPAMIENTO_PROFESIONAL`, `SOLAPAMIENTO_SILLON`, `TRANSICION_INVALIDA`).
  - `422`: Rechazo por formato o tipos de datos inválidos (`VALIDACION`).
- **Envelope estable**: Todo error debe responder con el formato estándar `{"error": {"code": "...", "message": "..."}}`.

### Dimensión 2 — Pureza del Dominio (Cero Acoplamiento en `src/domain/`)

El dominio es el núcleo del sistema y debe mantenerse completamente aislado de tecnologías de infraestructura y presentación:

- **0 imports prohibidos**: Los módulos bajo `backend/src/domain/` **NO** deben importar:
  - Frameworks web: `fastapi`, `starlette`, `pydantic`.
  - Criptografía y tokens: `jwt`, `pyjwt`, `hashlib`, `passlib`, `bcrypt`.
  - Drivers y adaptadores de persistencia: `sqlite3`, `sqlalchemy`, `src.repositories`, `src.infrastructure`.
- **Verificación automatizada**: La regla debe comprobarse mediante guard tests específicos (p. ej., `tests/test_pureza_dominio.py`) inspeccionando el AST o imports de `src/domain/`.

### Dimensión 3 — Seguridad y Aislamiento Multi-Tenant

El aislamiento estricto entre clínicas (tenants) es una regla inviolable de arquitectura (`RN-05`, `D-01`):

- **Origen no falsificable del tenant**: El `tenant_id` utilizado en operaciones de negocio debe provenir obligatoriamente de la sesión autenticada (`ContextoUsuario` resuelto a partir de un token JWT válido).
- **Prohibición de parámetros libres**: Ningún endpoint de negocio protegido debe permitir inyectar o sobreescribir el tenant mediante parámetros de query, campos del cuerpo o cabeceras libres (como `X-Tenant-ID`).
- **Inyección en repositorios**: Todas las consultas y operaciones de persistencia ejecutadas en los adaptadores deben recibir y filtrar obligatoriamente por el `tenant_id` validado.
- **Pruebas de fuga inter-tenant**: Deben existir pruebas de integración que demuestren que un usuario del Tenant A no puede consultar, crear ni alterar datos del Tenant B.

### Dimensión 4 — Sincronización de Artefactos de Estado

La trazabilidad del proceso SDD exige que los artefactos reflejen el estado real del sistema:

- **`tasks.md`**: Todas las tareas ejecutadas deben estar marcadas como completadas (`- [x]`) y `openspec instructions apply --change "<name>" --json` debe reportar `state: "all_done"`.
- **`CHANGES.md`**: El registro del change en el roadmap debe coincidir con el avance (marcado como completado o con scope actualizado).
- **`.active-orchestrator-state.json`**: El campo `active_change` debe apuntar al change en curso con `phase`, `status`, `tests` y `next_action` sincronizados.

---

## 2. Comandos de Verificación (Criterio Verde)

La auditoría requiere la ejecución exitosa de los siguientes comandos sobre el proyecto:

```bash
# 1. Validación formal del change en OpenSpec
openspec validate <change-name> --strict

# 2. Verificación de tareas en OpenSpec
openspec instructions apply --change "<change-name>" --json

# 3. Verificación de la suite completa con cobertura sobre SQLite real
cd backend && pytest --cov=src

# 4. Verificación explícita de pureza del dominio
cd backend && pytest tests/test_pureza_dominio.py -v
```

---

## 3. Checklist de Auditoría

- [ ] **Fidelidad**: Todos los escenarios de `specs/**/*.md` tienen tests correspondientes en `backend/tests/`.
- [ ] **Contratos HTTP**: Se verifican códigos `200`/`201`, `401`, `403`, `409` y `422` con envelope `{"error": {"code": "...", "message": "..."}}`.
- [ ] **Pureza**: `src/domain/` tiene 0 dependencias de `fastapi`, `pydantic`, `sqlite3`, `jwt` e infraestructura.
- [ ] **Aislamiento**: El `tenant_id` se extrae de `ContextoUsuario` y no admite falsificación por cabeceras o parámetros.
- [ ] **Persistencia**: Repositorios filtran consistentemente por `tenant_id` en SQLite real sin mocks.
- [ ] **Tareas**: Todas las tareas de `tasks.md` están marcadas `[x]` (100% completadas).
- [ ] **Roadmap**: `CHANGES.md` refleja el estado y avance del change.
- [ ] **Orquestador**: `.active-orchestrator-state.json` está actualizado con la fase y métricas de test.
- [ ] **Suite Verde**: 100% de las pruebas pasan sin errores ni regresiones.

---

## 4. Salida Esperada de la Skill

Al ejecutarse, la skill debe emitir un informe estructurado y conciso con el siguiente formato:

```markdown
### Reporte de Trazabilidad OpenSpec (SDD) — `<change-name>`

| Dimensión | Estado | Observaciones / Evidencia |
|---|---|---|
| **1. Fidelidad Normativa** | ✅ CUMPLE / ❌ NO CUMPLE | Cobertura de escenarios y códigos HTTP (200, 401, 403, 409, 422). |
| **2. Pureza de Dominio** | ✅ CUMPLE / ❌ NO CUMPLE | 0 imports de frameworks en `src/domain/`. Guard tests verdes. |
| **3. Seguridad y Aislamiento** | ✅ CUMPLE / ❌ NO CUMPLE | `tenant_id` resuelto desde `ContextoUsuario`. Aislamiento verificado. |
| **4. Sincronización de Artefactos** | ✅ CUMPLE / ❌ NO CUMPLE | `tasks.md` (all_done), `CHANGES.md` y `.active-orchestrator-state.json`. |

#### Dictamen Final
> **DICTAMEN: [ APROBADO / REQUIERE ACCIÓN ]**
> *(Resumen en un párrafo indicando si el change está listo para `/opsx:archive` o detallando las acciones requeridas)*.
```

---

## 5. Fuera de alcance de esta skill

- Implementar código o corregir fallas detectadas (la skill audita y dictamina; las correcciones corresponden a la fase apply).
- Archivar o sincronizar especificaciones principales de forma autónoma (función exclusiva de `openspec-archive-change`).
- Validar reglas visuales o de interfaz de usuario cuando el change sea exclusivamente de backend/API.

