# Design

## Context

En el cambio `C-12` se introdujo la pantalla base de agenda (`Agenda.tsx`) con listado cronológico de turnos, filtros y modales de alta y reprogramación. Sin embargo, para visualizar la disponibilidad simultánea de consultorios y sillones en una jornada clínica (`F-06`, `flows.md` §7), se requiere una representación bidimensional en forma de grilla matricial (recursos en columnas × franjas horarias en filas).
El backend ya cuenta con los endpoints necesarios para obtener turnos (`/turnos`), profesionales (`/profesionales`), sillones (`/sillones`) y bloqueos (`/bloqueos`). Este diseño aborda la estructura de componentes, el cómputo de la matriz y la alternancia de vistas en el cliente web SPA.
Véase `proposal.md` para la motivación y objetivos de negocio.

## UI Mockups

Decision: no (project policy)

## Goals / Non-Goals

**Goals:**
- Implementar el componente reutilizable `GrillaMatricial.tsx` capaz de pivotar columnas por sillón o por profesional.
- Generar una escala horaria predecible (intervalos de 30 minutos de 08:00 a 20:00) y proyectar los turnos según su intervalo `[hora_inicio, hora_fin)`.
- Proveer un selector de vista en `Agenda.tsx` para alternar entre "Lista" y "Matriz" manteniendo el estado de filtros activo.
- Renderizar los bloqueos de sillones activos (`/bloqueos`) como celdas no disponibles con patrón visual inhabilitado.
- Permitir interacción directa: clic en celda libre abre `ModalNuevoTurno` con valores preseleccionados; clic en turno permite confirmar, cancelar, reprogramar o completar.
- Respetar aislamiento RBAC para usuarios con rol `Profesional` (fijando la vista a su recurso correspondiente).
- Mantener cobertura exhaustiva mediante pruebas unitarias y de integración en Vitest.

**Non-Goals:**
- No incluye soporte de arrastrar y soltar (drag & drop) para mover turnos en esta versión, priorizando accesibilidad y robustez de estados en click-to-edit.
- No modifica la persistencia del backend ni añade librerías de calendario pesadas de terceros.

## Decisions

### Decisión 1: Generación de grilla horaria pura con Tailwind CSS y Flexbox/Grid
- **Elección**: Construir la matriz utilizando CSS Grid / Flexbox nativo de Tailwind (`table` o `grid`), dividiendo la jornada en franjas horarias uniformes (30 minutos: 08:00, 08:30, ..., 20:00).
- **Alternativas consideradas**:
  - *FullCalendar / React-Big-Calendar*: Descartado para mantener el bundle liviano, evitar dependencias pesadas y asegurar consistencia visual con el Design System existente (`system-only`).

### Decisión 2: Algoritmo de mapeo de celdas y solapamientos
- **Elección**: Computar una matriz bidimensional en memoria: para cada recurso (columna) y franja horaria (fila), buscar si existe un turno que cubra el slot `hora_slot >= hora_inicio && hora_slot < hora_fin`, o un bloqueo de mantenimiento.
- **Alternativas consideradas**:
  - *Posicionamiento absoluto por coordenadas píxeles*: Descartado por fragilidad responsive y mayor complejidad de cálculo.

### Decisión 3: Alternancia de vista en `Agenda.tsx`
- **Elección**: Estado `modoVista: 'lista' | 'matriz'` en `Agenda.tsx`. Los filtros superiores de fecha y recursos son compartidos por ambos modos; el botón de switch permite alternar fluidamente sin recargar peticiones a la API.

## Risks / Trade-offs

- **[Riesgo: Turnos con duraciones no alineadas a 30 minutos (ej. 45 min o 15 min)]** → **Mitigación**: Los turnos se mapean a todos los slots que intersecan su intervalo semiabierto `[inicio, fin)`, mostrando el badge en el slot de inicio y extendiendo el indicador visual a los slots sucesivos o etiquetando la hora exacta en la celda.
- **[Riesgo: Gran cantidad de columnas en dispositivos móviles]** → **Mitigación**: Habilitar contenedor con desplazamiento horizontal (`overflow-x-auto`) y primera columna de horarios fija (`sticky left-0`).

