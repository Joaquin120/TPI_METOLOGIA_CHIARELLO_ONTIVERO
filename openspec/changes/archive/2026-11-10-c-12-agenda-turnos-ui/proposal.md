# Proposal

## Why

Para que el personal de recepción y los odontólogos puedan operar la agenda clínica del consultorio en el día a día desde la aplicación web SPA (`frontend/`), se requiere una interfaz de usuario interactiva y completa que reemplace la pantalla preliminar de marcador de posición (`Agenda.tsx`).

Actualmente, las capacidades de backend (`C-01` a `C-10`) y el shell de navegación frontend (`C-11`) están totalmente implementados y probados, pero los usuarios carecen de una interfaz gráfica para consultar la grilla de turnos, agendar nuevas citas con verificación visual de solapamientos, cambiar estados (confirmar, cancelar, completar) y reprogramar turnos. Este cambio provee la interfaz operativa de la agenda integrando los contratos de la API REST bajo un diseño accesible y sobrio (`system-only`).

## What Changes

- **Vista interactiva de Agenda (`Agenda.tsx`)**:
  - Barra de filtrado superior por fecha (con selector de fecha y atajos a "Hoy"), profesional y sillón (`F-02`).
  - Visualización de turnos en lista o tarjetas cronológicas con código de colores según su estado (`data-models.md` §4.1): verde para `CONFIRMADO`, ámbar para `PENDIENTE`, rojo para `CANCELADO` y gris para `COMPLETADO`.
- **Formulario y Modal de Alta de Turno (`F-01`)**:
  - Creación de turnos mediante selección guiada de paciente (búsqueda o selección del listado), profesional habilitado, sillón operativo, fecha y franja horaria semiabierta `[inicio, fin)`.
  - Captura y presentación clara de errores de solapamiento de negocio (`SolapamientoProfesionalError` / `SolapamientoSillonError` / 409) directamente en el formulario sin recargas.
- **Acciones y Transiciones de Estado sobre el Turno (`F-03`)**:
  - Botones de acción contextuales según el estado actual: confirmar turnos pendientes, cancelar turnos activos (notificando la liberación de horarios) y completar turnos atendidos.
- **Reprogramación de Turnos (`F-09`, `C-08`)**:
  - Modal de reprogramación que permite ajustar la fecha y horario de un turno existente respetando las validaciones del doble candado.
- **Contexto y Roles (RBAC en UI)**:
  - Para usuarios con rol `Profesional`, la agenda fija automáticamente el filtro a su propio `profesional_id` y restringe la consulta a sus turnos asignados.
  - Recepcionistas y Administradores disponen de control total sobre todos los recursos y filtros de la clínica.
- **Suite de Pruebas de Frontend (Vitest + Testing Library)**:
  - Pruebas funcionales en `frontend/src/test/agenda.test.tsx` que verifican la carga de turnos, la aplicación reactiva de filtros, la creación exitosa y con solapamiento, las transiciones de estado y la restricción por rol.

## Capabilities

### New Capabilities
- `cliente-agenda-turnos`: Interfaz visual interactiva de gestión y consulta de agenda de turnos en el cliente web, incluyendo filtrado multivariable, alta con validación de solapamiento, transiciones de estado y reprogramación.

### Modified Capabilities
*(Ninguna. Las especificaciones de backend existentes conservan sus requisitos normativos sin alteraciones).*

## Impact

- **Frontend**:
  - `frontend/src/pages/Agenda.tsx` (implementación de la vista principal operativa).
  - Componentes modales y de filtrado en `frontend/src/components/` (`ModalNuevoTurno.tsx`, `ModalReprogramarTurno.tsx`, `FiltrosAgenda.tsx`, `TarjetaTurno.tsx`).
  - Pruebas automatizadas en `frontend/src/test/agenda.test.tsx`.
- **Backend**: Ningún cambio en el código del servidor; se consumen los endpoints existentes de `/turnos`, `/profesionales`, `/sillones` y `/pacientes`.

