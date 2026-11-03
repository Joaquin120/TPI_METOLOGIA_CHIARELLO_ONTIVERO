# Ficha de investigación — Parte 1: Skills y Servidores MCP

> **Proyecto**: turnos-odontologia (TP Metodología I) · **Fecha de consulta**: 2 de noviembre de 2026
> **Alcance máximo**: 2 páginas

---

## 1. Necesidad detectada y Change seleccionado

**Change seleccionado**: `C-01 cancelacion-y-estados-turno` — `CHANGES.md`, FASE 0 · Núcleo del dominio (governance MEDIO).

**Justificación**:

- Es el **primer change del camino crítico MVP** (`C-01 → C-02 → C-03 → …`) y **no tiene dependencias previas** (`Dependencias: ninguna`).
- **Continúa directo** de la base archivada `2026-10-15-crear-turno-sin-solapamientos`, que dejó el servicio de dominio `ServicioTurnos` con alta y validación de solapamientos; C-01 agrega el ciclo de vida completo del turno.
- Su scope toca `RN-03` (ciclo de estados) y `RN-04` (liberación por cancelación), reglas de dominio críticas para el resto de la cadena.

**Necesidad de una skill**: la matriz de estados (`PENDIENTE`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`) y sus transiciones (`Confirmar`, `Cancelar`, `Completar`) son fáciles de codificar incompletamente o con casos de borde omitidos. La skill evita:

- Errores en la matriz de estados (`RN-03`): transiciones inválidas admitidas por accidente, o estados finales que siguen admitiendo movimientos (debe lanzar `TransicionInvalidaError`).
- Casos de borde omitidos en `RN-04`: la **liberación del intervalo semiabierto `[T_inicio, T_fin)`** al cancelar — el filtro de solapamiento debe excluir turnos `CANCELADO`/`COMPLETADO` y permitir re-reserva inmediata en el mismo intervalo, sin correr el borde de igualdad en los extremos (D-07).

**Necesidad del MCP**: el agente debe **consultar con precisión** el código existente (`src/`, `tests/`) y las especificaciones previas (`openspec/specs/crear-turno/spec.md`, `knowledge-base/`) sin inventar funciones, rutas o nombres de métodos que aún no existen.

---

## 2. Skill creadora investigada y diseño de la skill propia

**Skill creadora**: `skill-creator` — repositorio oficial **anthropics/skills** (`https://github.com/anthropics/skills`). Proporciona la plantilla y el flujo para crear skills estructuradas (descripción de disparo, instrucciones, recursos) con metadatos YAML y evaluaciones de trigger.

**Skill propia**: **`domain-state-matrix-validator`**

| Campo | Contenido |
|---|---|
| **Propósito** | Validar la coherencia de la matriz de transiciones de estados del turno (`RN-03`) y **generar los 3 escenarios formales Spec-Driven** exigidos por el cambio: (1) transición válida — esperada; (2) transición inválida — error de negocio con `TransicionInvalidaError`; (3) caso de borde de **re-reserva inmediata** tras cancelación (liberación de `[T_inicio, T_fin)`). |
| **Cuándo se activa** | Al redactar `specs/`, `proposal.md` y `design.md` de changes que toquen turnos o recursos (estados, cancelación, disponibilidad). |
| **Entradas** | `knowledge-base/business-rules.md` §RN-03/§RN-04, §D-07 (intervalos semiabiertos); specs `openspec/specs/crear-turno/spec.md`; código de `src/` y `tests/` existentes. |
| **Procedimiento** | 1) Extraer estados y transiciones declaradas en la KB. 2) Contrastarlas con la matriz propuesta en la spec (completitud y ausencia de transiciones fantasma). 3) Verificar que todo estado final sea absorbente. 4) Verificar que el filtro de solapamiento excluya estados no activos con criterio `[inicio, fin)`. 5) Redactar los 3 escenarios con Given/When/Then. |
| **Resultado esperado** | Matriz validada + 3 escenarios Spec-Driven listos para pegar en la spec del change; lista de hallazgos si hay incoherencias. |
| **Criterios de revisión** | Cada par origen→destino está clasificado (válida/inválida); los 3 escenarios presentes y verificables por test; re-reserva en idéntico intervalo cubierta; sin contradicciones con `RN-03`, `RN-04`, `D-07`. |
| **Ubicación** | `.atl/skills/domain-state-matrix-validator.md`, registrada en `.atl/skill-registry.md`. |

---

## 3. Comparación y selección del servidor MCP

| Criterio | **Filesystem MCP** (`@modelcontextprotocol/server-filesystem`) | **Fetch MCP** (`@modelcontextprotocol/server-fetch`) |
|---|---|---|
| Propósito | Lectura/escritura de archivos y directorios locales | Descargar contenido de URLs HTTP(S) como texto/HTML/Markdown |
| Herramientas | `read_file`, `read_multiple_files`, `write_file`, `edit_file`, `list_directory`, `search_files`, `directory_tree`… | `fetch` (con `url`, `format`, `max_length`, certificados personalizados) |
| Compatibilidad | Cliente MCP con `npx` (Node 18+); funciona con OpenCode/Claude Desktop | Igual: `npx`, cualquier cliente MCP |
| Requisitos | Node.js + paquete npm; directorios raíz declarados en la config | Node.js + paquete npm; acceso de red saliente |
| Permisos | Acotado a rutas **raíz explícitas** del config (fuera de ellas, deniega) | Acceso a cualquier URL pública alcanzable |
| Credenciales | Ninguna | Ninguna (sitios con auth requieren headers propios) |
| Costo | Gratuito, open source | Gratuito, open source |
| **Riesgo** | Escritura sobre el repo si se habilita | Hacia fuera: fuga de contexto, contenido no verificado |

**Elección justificada**: **Filesystem MCP**. La necesidad detectada (punto 1) es **lectura local estructurada** de la base de conocimiento y del código existente del repo — justamente lo que Filesystem hace con `read_file`/`search_files`/`directory_tree`, con permisos por raíz. Fetch no aporta a esta parte (no hay investigación web en el flujo) y sumaría superficie de red innecesaria.

**Límites de seguridad**: raíz acotada al directorio local del repo; **solo lectura** (no se usan `write_file`/`edit_file`); **sin datos sensibles** en el repo (regla dura 3: solo datos sintéticos) y sin secretos en config (D-05).

---

## 4. Pasos previstos de instalación/configuración

**Configuración JSON del cliente** (OpenCode: `opencode.json` / Claude Desktop: `claude_desktop_config.json`), con el directorio raíz del proyecto:

```json
{
  "mcp": {
    "filesystem": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem",
                  "/home/joaquin/Documentos/TPI_CHIARELLO_OLIVEROS_ONTIVERO_RODRIGUEZ_METODOLOGIA1"],
      "environment": {},
      "enabled": true
    }
  }
}
```

Pasos: 1) Verificar Node.js 18+. 2) Agregar el bloque anterior al config del cliente. 3) Reiniciar el cliente y confirmar las tools de filesystem listadas. 4) Verificar lectura de `knowledge-base/` y `openspec/specs/`. 5) **No** habilitar tools de escritura en esta fase.

**Archivos de la fundación a actualizar**:

- `.atl/skill-registry.md` — registrar `domain-state-matrix-validator` (ruta, trigger, propósito).
- `AGENTS.md` / `CLAUDE.md` — fila de la skill en la tabla de skills por agente y nota del MCP disponible.
- `README.md` — sección de skills y servidores MCP del proyecto, con pasos de configuración.

---

## 5. Fuentes consultadas

| Fuente | URL | Fecha de consulta |
|---|---|---|
| Repositorio oficial de skills (skill-creator) | https://github.com/anthropics/skills | 02/11/2026 |
| Filesystem MCP (server) | https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem | 02/11/2026 |
| Fetch MCP (server) | https://github.com/modelcontextprotocol/servers/tree/main/src/fetch | 02/11/2026 |
| Especificación MCP | https://modelcontextprotocol.io/ | 02/11/2026 |
| npm: @modelcontextprotocol/server-filesystem | https://www.npmjs.com/package/@modelcontextprotocol/server-filesystem | 02/11/2026 |
| npm: @modelcontextprotocol/server-fetch | https://www.npmjs.com/package/@modelcontextprotocol/server-fetch | 02/11/2026 |
| OpenCode — MCP servers | https://opencode.ai/docs/mcp-servers/ | 02/11/2026 |
| Registro interno: `CHANGES.md`, `knowledge-base/business-rules.md` | repositorio local del TP | 02/11/2026 |
