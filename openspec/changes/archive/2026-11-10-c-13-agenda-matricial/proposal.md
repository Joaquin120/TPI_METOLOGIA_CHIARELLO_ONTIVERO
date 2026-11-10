# Proposal

## Why

Para optimizar la coordinación clínica y la toma de decisiones visual en el consultorio odontológico, el personal de recepción y los profesionales necesitan una vista matricial bidimensional cruzada (franjas horarias × recursos) que complemente la lista cronológica introducida en el MVP (`C-12`).

Actualmente, la vista de agenda muestra los turnos en forma de tarjetas lineales. Si bien esto permite consultar y gestionar turnos individuales, dificulta identificar de un vistazo huecos libres simultáneos en los sillones, superposiciones potenciales entre profesionales y períodos bloqueados por mantenimiento técnico (`F-06`, `flows.md` §7). La vista matricial resuelve esta limitación ofreciendo una grilla horaria interactiva y de alta densidad visual.

## What Changes

- **Alternancia de vistas en Agenda (`Agenda.tsx`)**:
  - Selector de modo de visualización: alternancia fluida entre "Vista Lista" y "Vista Matricial".
- **Grilla Matricial Interactiva (`GrillaMatricial.tsx`)**:
  - Eje vertical con franjas horarias configurables (granularidad de 30 minutos entre las 08:00 y las 20:00).
  - Eje horizontal con columnas segmentables por Recurso: modo agrupación por "Sillones" o por "Profesionales".
  - Celdas con renderizado visual de turnos codificados por color de estado (verde para `CONFIRMADO`, ámbar para `PENDIENTE`, rojo para `CANCELADO`, gris para `COMPLETADO`).
- **Integración de Bloqueos de Sillón (`C-10` / `/bloqueos`)**:
  - En la vista matricial por sillones, visualización de slots bloqueados por mantenimiento preventivo con indicador visual destacado (patrón rayado o badge de advertencia) y descripción del motivo.
- **Interacción rápida desde celdas**:
  - Clic en turno existente dentro de la celda: abre el detalle o modal de acciones contextuales (confirmar, reprogramar, cancelar).
  - Clic en celda horaria libre: dispara el modal de alta (`ModalNuevoTurno`) preseleccionando automáticamente la fecha, franja horaria y el sillón o profesional correspondiente a dicha columna.
- **Control RBAC y accesibilidad responsive**:
  - Si el usuario autenticado tiene rol `Profesional`, la matriz bloquea la consulta a su profesional asignado y destaca sus franjas de atención.
  - Diseño responsive y scroll horizontal contenido con cabeceras de columnas fijas (`sticky`).

## Capabilities

### New Capabilities
*(Ninguna nueva capability independiente; se consolida y extiende la capacidad de agenda del cliente web).*

### Modified Capabilities
- `cliente-agenda-turnos`: Incorpora requerimientos normativos para la visualización matricial de turnos por franja horaria y recursos, alternancia entre vista de lista y matriz, renderizado de bloqueos de sillones por mantenimiento, e interacción directa sobre celdas para agendamiento rápido.

## Impact

- **Frontend**:
  - `frontend/src/components/GrillaMatricial.tsx` (nuevo componente de grilla matricial horaria).
  - `frontend/src/pages/Agenda.tsx` (incorporación de switch lista/matriz y coordinación de estados).
  - `frontend/src/types/index.ts` (tipos auxiliares para franjas horarias y celdas matriciales).
  - `frontend/tests/grilla-matricial.test.tsx` y `frontend/tests/agenda.test.tsx` (pruebas funcionales con Vitest y React Testing Library).
- **Backend / APIs**: Sin cambios en el backend; se consumen los endpoints existentes de `/turnos`, `/bloqueos`, `/profesionales` y `/sillones`.

