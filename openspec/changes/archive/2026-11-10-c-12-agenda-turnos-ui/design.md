# Design

## Context

El frontend de la aplicación clínica cuenta actualmente con la configuración base de React Router, autenticación con JWT y cliente Axios estructurado (`frontend/src/api/`). La pantalla `Agenda.tsx` existente actúa solo como un marcador de posición estático.
Para satisfacer los requisitos funcionales de consulta y gestión de turnos (`F-01`, `F-02`, `F-03`, `F-09`), se diseñará una arquitectura de componentes modulares y reactivos que consuman los endpoints REST expuestos en el backend (`/turnos`, `/turnos/{id}/confirmar`, `/turnos/{id}/cancelar`, `/turnos/{id}/completar`, `/turnos/{id}/reprogramar`, `/profesionales`, `/sillones`, `/pacientes`).
Véase `proposal.md` para la motivación de negocio y justificación.

## UI Mockups

Decision: no (project policy)

## Goals / Non-Goals

**Goals:**
- Proveer una vista de agenda interactiva y fluida (`Agenda.tsx`) con filtros reactivos por fecha, profesional y sillón.
- Modularizar los componentes visuales: barra de filtros (`FiltrosAgenda.tsx`), tarjeta de turno (`TarjetaTurno.tsx`), modal de creación (`ModalNuevoTurno.tsx`) y modal de reprogramación (`ModalReprogramarTurno.tsx`).
- Integrar visualmente los tokens de diseño definidos en `design-system/tokens.css` (colores de estado para turnos: verde confirmación, ámbar pendiente, rojo cancelación, gris completado).
- Brindar retroalimentación inmediata al usuario ante errores de solapamiento (código HTTP 409 con detalle de conflicto por profesional o sillón).
- Asegurar aislamiento de visibilidad por rol (RBAC en cliente): si el usuario autenticado tiene rol `Profesional`, limitar la visualización y filtrado exclusivamente a su identificador asignado.
- Garantizar cobertura con pruebas funcionales de interfaz mediante Vitest y React Testing Library (`frontend/src/test/agenda.test.tsx`).

**Non-Goals:**
- No incluye integración con librerías externas pesadas de calendario complejo (como FullCalendar) para mantener el bundle liviano y minimizar dependencias; se implementa una grilla/lista operativa limpia y accesible con Tailwind CSS.
- No incluye notificaciones por canales externos (WhatsApp / SMS / Email), las cuales corresponden a integraciones desacopladas del backend.
- No altera los esquemas de base de datos ni los endpoints existentes del backend.

## Decisions

### Decisión 1: Estructura de estado en `Agenda.tsx` y subcomponentes desacoplados
- **Elección**: Manejar el estado de filtros (`fechaSeleccionada`, `profesionalId`, `sillonId`) y la lista de turnos en `Agenda.tsx`, delegando la renderización y captura de eventos a componentes puros e hijos (`FiltrosAgenda`, `TarjetaTurno`, `ModalNuevoTurno`, `ModalReprogramarTurno`).
- **Alternativas consideradas**:
  - *Estado global en Redux / Zustand*: Descartado por añadir complejidad innecesaria para una vista local cuyos datos se sincronizan directamente con la API REST.
  - *Componente monolítico en un único archivo*: Descartado para facilitar la mantenibilidad y permitir pruebas unitarias y de integración modulares.

### Decisión 2: Consumo de endpoints y cliente de API
- **Elección**: Reutilizar el módulo `frontend/src/api/turnos.ts` extendiéndolo con las funciones tipadas necesarias (`getTurnos`, `crearTurno`, `confirmarTurno`, `cancelarTurno`, `completarTurno`, `reprogramarTurno`), así como los clientes de recursos auxiliares (`profesionales.ts`, `sillones.ts`, `pacientes.ts`).
- **Alternativas consideradas**:
  - *Llamadas directas con `fetch` inline*: Descartado por duplicación de cabeceras de autorización y manejo de errores.

### Decisión 3: Manejo y visualización de errores de solapamiento (409)
- **Elección**: En los formularios modales (alta y reprogramación), capturar el error `AxiosError` con status 409 y extraer el mensaje del campo `response.data.detail` para exhibirlo en una alerta destacada en rojo dentro del modal, evitando su cierre para que el operador pueda ajustar el horario sin perder los datos cargados.
- **Alternativas consideradas**:
  - *Alert genérico del navegador (`window.alert`)*: Descartado por mala experiencia de usuario y falta de accesibilidad.

### Decisión 4: Uso de variables y clases del Design System
- **Elección**: Aplicar las clases y variables CSS definidas en `design-system/tokens.css` y las utilidades de Tailwind CSS ya configuradas para reflejar fielmente los colores institucionales y los estados de los turnos (`--color-status-success`, `--color-status-warning`, `--color-status-danger`, `--color-status-info`).

## Risks / Trade-offs

- **[Riesgo: Volumen alto de turnos en una misma fecha]** → **Mitigación**: Ordenar cronológicamente por `hora_inicio` y permitir filtrado inmediato por profesional y sillón para segmentar la grilla de manera clara y sin degradación de rendimiento.
- **[Riesgo: Discrepancia horaria de zona horaria local vs UTC en navegadores]** → **Mitigación**: Manejar y enviar las fechas y horas en formato estándar ISO / strings locales (`YYYY-MM-DD` y `HH:MM`) alineados con los esquemas Pydantic del backend.
- **[Riesgo: Inconsistencia si dos recepcionistas toman el mismo horario simultáneamente]** → **Mitigación**: El backend implementa transacción con nivel Serializable y doble candado; el frontend captura limpiamente el 409 y alerta al segundo operador inmediatamente.

