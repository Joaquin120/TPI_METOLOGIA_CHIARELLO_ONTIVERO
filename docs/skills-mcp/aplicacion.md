# Informe de aplicación — Skills y MCP (Parte 2)

> **Proyecto**: turnos-odontologia · **Change preparado**: `c-01-cancelacion-y-estados-turno` · **Fecha**: 02/11/2026 · **Extensión**: ≤ 2 páginas

---

## 1. Resultados y evidencia de uso

### Evidencia de la skill `domain-state-matrix-validator`

La skill (`.atl/skills/domain-state-matrix-validator.md`) fue aplicada durante la preparación del change C-01 para diseñar la máquina de estados y los escenarios:

- **Matriz de transiciones (RN-03/RN-04)**: lista blanca de pares (estado, acción) → destino, con los 4 estados (`PENDIENTE`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`) y efecto sobre recursos por arista. `CANCELADO` y `COMPLETADO` quedan como **estados absorbentes**: cualquier transición saliente se rechaza con `TransicionInvalidaError`. El efecto "libera" se asignó a `CONFIRMADO → CANCELADO` y `CONFIRMADO → COMPLETADO` (RN-04), cubriendo **profesional y sillón simultáneamente** (regla dura 2).
- **Salida**: la matriz completa y el contrato de la excepción quedaron plasmados en `design.md`; la redacción de escenarios, en la spec delta.

### Escenarios en `openspec/changes/c-01-cancelacion-y-estados-turno/specs/gestionar-estados-turno/spec.md`

**7 escenarios Given/When/Then** en 3 requirements, incluyendo los 3 obligatorios:

| # | Tipo | Escenario |
|---|------|-----------|
| 1 | Esperado | `CONFIRMADO → CANCELADO` libera el intervalo semiabierto `[T_inicio, T_fin)` (recurso profesional y sillón) |
| 2 | Error de negocio | Intento `CANCELADO → COMPLETADO` → `TransicionInvalidaError`, estado intacto |
| 3 | Caso de borde | Re-reserva inmediata del **mismo profesional y sillón** dentro del intervalo liberado **y** contigua en `T_fin` |
| 4–7 | Extras | `confirmar()` y `completar()` válidos; rechazo desde `COMPLETADO`; alta no bloqueada por turno cancelado |

### Evidencia del MCP Filesystem

Ejecución real del servidor `@modelcontextprotocol/server-filesystem` por stdio/JSON-RPC (sin credenciales, raíz = repo):

- `tools/list` → 14 tools confirmadas, entre ellas `list_directory`, `read_file`/`read_text_file`, `get_file_info`.
- `list_directory` sobre `openspec/changes/archive/` → `[FILE] .gitkeep` / `[DIR] 2026-10-15-crear-turno-sin-solapamientos`.
- `get_file_info` + `read_text_file` sobre el `proposal.md` del change archivado → tamaño 583 B, permisos 664, y su contenido real ("Crear Turno Evitando Solapamientos por Profesional y por Sillón/Box… intervalo semiabierto `[Inicio, Fin)`").

Contraaste con el change archivado **sin inventar estructuras**: los artefactos previos se leyeron tal cual existen en disco, lo que permitió verificar que C-01 continúa la línea de D-07 (semiabiertos) y el patrón de excepciones existente.

---

## 2. Revisión crítica (antes vs. después)

| # | Desviación detectada | Antes | Después (corrección) |
|---|----------------------|-------|----------------------|
| a | **Transiciones desde estados terminales** | Riesgo de que `CANCELADO`/`COMPLETADO` volvieran a `CONFIRMADO` (p. ej. "reabrir") sin rechazo explícito | Regla de lista blanca: solo los 4 pares de RN-03 son válidos; todo lo demás → `TransicionInvalidaError`. Cubierto en `design.md` (matriz) y en 2 escenarios de error de la spec |
| b | **Nombre del change en mayúsculas** | El usuario pidió la ruta `openspec/changes/C-01-cancelacion-y-estados-turno/`; el CLI rechazó: *"Change name must be lowercase (use kebab-case)"* | Creado como `c-01-cancelacion-y-estados-turno` (kebab-case). Desviación documentada en el resumen y en engram |
| c | **Warnings de idioma en keywords** | El validador de openspec 1.16 solo reconoce `GIVEN/WHEN/THEN` en inglés; los escenarios usan `Dado/Cuando/Entonces` → warnings en `openspec validate` | Verificado que la **spec main `crear-turno` ya emite los mismos warnings** (convención existente del repo); se mantuvo el español. `--strict` queda como decisión pendiente del equipo |

---

## 3. Lista de archivos creados y modificados

| Archivo | Acción | Motivo |
|---------|--------|--------|
| `.atl/skills/domain-state-matrix-validator.md` | Creado | Skill propia: matriz RN-03/RN-04 + 3 escenarios formales |
| `.atl/skill-registry.md` | Modificado | Registrar la skill (sección Project Local Skills + compact rules) |
| `AGENTS.md` | Modificado | Secciones "Uso de Skills Locales" e "Integración Externa: MCP Filesystem" |
| `CLAUDE.md` | Modificado | Espejo idéntico de AGENTS.md (copia declarada) |
| `README.md` | Modificado | Sección "Integración MCP: Filesystem Server" (config, verificación, troubleshooting) |
| `docs/skills-mcp/investigacion.md` | Creado | Ficha de investigación Parte 1 (change, skill, MCP, fuentes) |
| `docs/skills-mcp/aplicacion.md` | Creado | Este informe de aplicación |
| `openspec/changes/c-01-cancelacion-y-estados-turno/proposal.md` | Creado | Justificación, alcance, reglas e impacto del change |
| `.../specs/gestionar-estados-turno/spec.md` | Creado | Delta spec: 3 requirements, 7 escenarios Given/When/Then |
| `.../design.md` | Creado | Máquina de estados, matriz, `TransicionInvalidaError`, liberación `[T_inicio, T_fin)` |
| `.../tasks.md` | Creado | Plan TDD secuencial con comando de verificación por tarea |

---

## 4. Limitaciones y conclusiones

- El change quedó **preparado formalmente y validado**: `openspec validate` → *"Change is valid"*, los 4 artefactos en `done` y `isPlanningComplete: true`.
- **Sin implementar**: no se escribió código de producción en `backend/src/` ni tests nuevos (Spec First); `CHANGES.md` no se tocó y no se archivó el change.
- **Baseline intacto**: la suite de **8 tests verdes** no se alteró (verificada antes y después de la preparación).
- Limitaciones: ruta del change en minúsculas (imposición del CLI), warnings de keywords en español (convención preexistente) y decisión pendiente sobre `PA-13` (estado inicial del alta) que queda abierta fuera del alcance.
- **Conclusión**: la skill aportó la matriz y los escenarios formales; el MCP aportó lectura verificable del repo y del change archivado. El change C-01 está listo para la fase de implementación (`/opsx:apply`) bajo TDD estricto.
