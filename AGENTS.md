# turnos-odontologia — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

---

## Stack Tecnológico

| Capa | Tecnología | Versión | Estado |
|------|------------|---------|--------|
| Lenguaje del núcleo | Python (type hints, PEP 8) | 3.11+ | Definido (D-03) |
| Backend / API | FastAPI (candidato) — Python/FastAPI vs. Node.js | — | **Pendiente (DP-01)** |
| Desarrollo y pruebas | SQLite | — | Definido (D-04) |
| Producción / ORM / migraciones | Por definir | — | **Pendiente (DP-02)** |
| Frontend | Web-first (framework por definir) | — | Fases 4-5 del roadmap |
| Integraciones | WhatsApp (recordatorios) | — | Segunda etapa (DP-09) |
| Configuración | Variables de entorno (`.env`) — sin secretos en el repo | — | Definido (D-05) |

Detalle completo: [knowledge-base/decisions.md](knowledge-base/decisions.md) · [knowledge-base/architecture.md](knowledge-base/architecture.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [vision.md](knowledge-base/vision.md) | Entender propósito y alcance |
| [description.md](knowledge-base/description.md) | Descripción general, módulos, límites del MVP |
| [actors.md](knowledge-base/actors.md) | Auth, RBAC, permisos |
| [data-models.md](knowledge-base/data-models.md) | Entidades, ERD, migraciones |
| [business-rules.md](knowledge-base/business-rules.md) | Reglas codificadas (RN-XX) |
| [features.md](knowledge-base/features.md) | Historias de usuario por épica |
| [flows.md](knowledge-base/flows.md) | Flujos E2E |
| [architecture.md](knowledge-base/architecture.md) | Patrones, estructura, env vars |
| [decisions.md](knowledge-base/decisions.md) | Decisiones (D-XX) y pendientes (DP-XX) |
| [open-questions.md](knowledge-base/open-questions.md) | ⚠️ Inconsistencias a resolver ANTES de codear |

> ⚠️ Resolver las preguntas de prioridad **Alta** de `open-questions.md` antes de arrancar el primer change (`PA-13`, `PA-10`, `PA-06`, `PA-05`, `PA-04`, `RP-07`, `DP-01`, `DP-02`, `DP-03`, `DP-04`).

---

## Skills Disponibles

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | Dominio, API, persistencia | `fastapi`, `python-testing-patterns`, `clean-architecture`, `domain-driven-design`, `sqlalchemy-alembic-expert-best-practices-code-review` |
| **Orquestación** | SDD / OPSX / discovery | `discovery-research`, `web-scraper` + skills OpenSpec (`openspec-propose`, `openspec-apply-change`, `openspec-archive-change`, …) |

Cargá la skill correspondiente al contexto ANTES de escribir código.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — no está en el repo). Esta tabla solo mapea skill→rol.

---

## Uso de Skills Locales

Skills propias del proyecto, vivas en `.atl/skills/` y registradas en `.atl/skill-registry.md`.

### `domain-state-matrix-validator` — `.atl/skills/domain-state-matrix-validator.md`

**Cuándo invocarla**: al redactar o revisar `proposal.md`, `design.md` o `specs/` de cualquier change que defina o modifique **estados y transiciones de turnos o recursos** (en especial `C-01 cancelacion-y-estados-turno`). Nunca escribir la máquina de estados ni sus tests sin pasar antes por esta skill.

**Insumos de `knowledge-base/` a consultar ANTES de usarla**:

- `knowledge-base/business-rules.md` → §RN-03 (matriz de transiciones), §RN-04 (liberación por cancelación), §RN-02/§RN-09 (solapamiento).
- `knowledge-base/data-models.md` → §4.1 Estado del turno.
- `knowledge-base/decisions.md` → `D-07` (intervalos semiabiertos `[inicio, fin)`).
- `openspec/specs/crear-turno/spec.md` → spec vigente del alta (`PA-13` abierta: no resolver en el change).

**Cómo verificar el resultado**: la salida debe incluir **los 3 escenarios formales en formato Given/When/Then**, sin excepciones:

1. **Esperado**: `CONFIRMADO → CANCELADO` libera el intervalo `[T_inicio, T_fin)`.
2. **Error de negocio**: `CANCELADO → COMPLETADO` lanza `TransicionInvalidaError`.
3. **Caso de borde**: re-reserva exitosa del mismo profesional y sillón en el intervalo semiabierto liberado por la cancelación.

Y debe cumplir, sin romper el **criterio verde** (regla dura 4): la suite existente (`backend/tests/`, `pytest`) pasa al 100% después de incorporar los escenarios como tests nuevos — verificar con `cd backend && pytest` antes de dar por terminada la tarea. La excepción `TransicionInvalidaError` debe seguir el patrón de `backend/src/domain/exceptions.py`.

---

## Integración Externa: MCP Filesystem

El proyecto se integra con el servidor MCP **Filesystem** (`@modelcontextprotocol/server-filesystem`) como **integración externa de herramientas**. Configuración y troubleshooting: `README.md` § "Integración MCP: Filesystem Server".

- **Propósito**: inspección del repositorio local (archivos reales, sin alucinaciones) — `knowledge-base/`, `openspec/specs/`, `openspec/changes/archive/` y el código bajo `backend/`.
- **Herramientas disponibles**: `list_directory`, `read_file`, `get_file_info`.
- **Cuándo usarlo**: **antes de redactar propuestas o especificaciones**, para verificar código y contratos existentes (nombres de clases/excepciones en `backend/src/domain/exceptions.py`, estados y reglas en la KB, specs vigentes) en lugar de asumirlos de memoria.
- **Límites**: acceso **confinado a la raíz del repositorio** (rutas absolutas; fuera de la raíz se deniega) y **solo lectura** sobre documentación y código base — el MCP nunca se usa para escribir ni modificar archivos.

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 15 changes en 6 fases (FASE 0-4 = MVP, FASE 5 = segunda etapa).
- **Camino crítico MVP** (7): `C-01 cancelacion-y-estados-turno → C-02 persistencia-sqlite → C-03 capa-api-desacoplada → C-04 auth-rbac-tenancy → C-05 endpoints-turnos → C-11 frontend-shell → C-12 agenda-turnos-ui`.
- **Primer change**: `C-01` (`cancelacion-y-estados-turno`).
- **Completado**: `2026-10-15-crear-turno-sin-solapamientos` ✔ archivado · `2026-11-03-c-01-cancelacion-y-estados-turno` ✔ archivado · `2026-11-03-c-02-persistencia-sqlite` ✔ archivado · `2026-11-04-c-03-api-fastapi` ✔ archivado · `2026-11-05-c-04-auth-rbac-tenancy` ✔ archivado · `2026-11-08-c-05-endpoints-turnos` ✔ archivado · `2026-11-09-c-06-endpoints-recursos` ✔ archivado · `2026-11-09-c-07-gestion-pacientes` ✔ archivado (specs en `openspec/specs/gestionar-pacientes/spec.md`).

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras (específicas del proyecto)

> No existe `~/.claude/CLAUDE.md` global en este entorno: TODAS las reglas (universales y específicas) se listan acá. Si se instala un global después, migrar las universales para no duplicar.

Inviolables (ya vigentes — ver también el historial de reglas del proyecto):

1. **Spec First** → NUNCA escribir ni modificar código en `src/` ni tests en `tests/` sin una especificación aprobada en `openspec/changes/`.
2. **Doble validación de recurso** → NUNCA validar solo el profesional: la disponibilidad verifica **Profesional y Sillón/Box de forma simultánea e independiente**.
3. **Privacidad** → NUNCA almacenar ni procesar datos reales de pacientes o profesionales en el repo, fixtures o history clínica; solo datos sintéticos (`Paciente Ficticio`, `Dr. Ejemplo`).
4. **Suite verde** → NUNCA dar por finalizada una tarea si `tests/` presenta fallas (`pytest` / `pytest --cov=src`).

Confirmadas con el usuario (stack-aware + universales no cubiertas por global):

5. **Tests contra SQLite real** → NUNCA mockear la base de datos en tests: usar la base real (D-04); la doble validación se prueba contra persistencia real.
6. **Sin secretos en el repo** → NUNCA commitear credenciales: configuración exclusivamente por `.env`/variables de entorno (D-05).
7. **Intervalos semiabiertos** → NUNCA usar intervalos cerrados en solapamientos: aplicar `[inicio, fin)` (`inicio_a < fin_b AND fin_a > inicio_b`) en todo el código (D-07).
8. **Tenant siempre presente** → NUNCA persistir ni consultar entidades sin considerar `tenant_id` (D-01).
9. **Conventional Commits** → NUNCA commitear mensajes libres: usar `feat`/`fix`/`test`/`docs`/`refactor`/`chore` (sin co-autoría IA).
10. **No buildear/pushear sin pedir** → NUNCA correr builds, deploys ni `git push` sin confirmación explícita del usuario.

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio
2. Identificar el change en CHANGES.md           → respetar dependencias y GATEs
3. /opsx:propose C-NN-nombre                     → proposal + design + specs + tasks
4. Implementar las tasks (cargando skills)       → TDD estricto, respetando las reglas duras
5. /opsx:archive C-NN-nombre + marcar [x]        → cerrar el change
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
