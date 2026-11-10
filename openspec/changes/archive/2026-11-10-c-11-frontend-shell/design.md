# Design

## Context

El producto está concebido como una plataforma SaaS web-first (`architecture.md` §1, `actors.md` §4, `D-01`), orientada a recepcionistas, administradores y odontólogos de consultorios y clínicas. Todas las capacidades de negocio (`C-01` a `C-10`) han sido implementadas y probadas exhaustivamente en la API REST/JSON de FastAPI (`backend/`), contando con 303 pruebas unitarias y de integración pasando al 100%.

En la base de conocimiento se documentó la decisión pendiente `DP-01` (framework y stack para el cliente web). Habiéndose completado el núcleo del backend, este cambio define la arquitectura del cliente web SPA en `frontend/`, implementando la autenticación JWT (`POST /api/v1/auth/login`), la gestión de sesión, el control de acceso basado en roles (RBAC) y la navegación responsiva contextual (`Recepcionista`, `Administrador`, `Profesional`), dejando la base lista para la agenda interactiva de turnos (`C-12`).

## Goals / Non-Goals

**Goals:**
- Configurar el entorno de desarrollo y compilación del frontend en `frontend/` mediante Vite, React 18+ y TypeScript estricto.
- Implementar un cliente HTTP centralizado y tipado (`api/cliente.ts`) sobre la API REST existente, con inyección automática de cabecera `Authorization: Bearer <token>`, manejo uniforme de errores según el envelope de la API y captura reactiva de respuestas HTTP 401 para cierre de sesión.
- Implementar la gestión de estado de autenticación (`AuthContext.tsx`) con persistencia local del token y datos del usuario logueado (`id`, `email`, `rol`, `tenant_id`, `nombre`).
- Implementar un guardián de rutas (`ProtectedRoute.tsx`) con React Router DOM v6 para proteger vistas privadas y restringir accesos según roles autorizados.
- Desarrollar el layout general de la aplicación (`Layout.tsx`, `Navbar.tsx`, `Sidebar.tsx`) con navegación contextual diferenciada según el rol del usuario autenticado.
- Proveer vistas base para Inicio de Sesión (`/login`), Agenda (`/agenda`), Pacientes (`/pacientes`), Recursos (`/recursos`) y Auditoría (`/auditoria`), preparadas para recibir sus componentes operativos en los changes subsiguientes.
- Establecer una suite de pruebas automatizadas con Vitest y Testing Library que verifique el flujo de autenticación, la redirección de rutas y el cumplimiento de RBAC en el cliente.

**Non-Goals:**
- Implementar la grilla visual interactiva y los selectores horarios de la agenda (alcance específico de `C-12 agenda-turnos-ui`).
- Implementar formularios completos de alta/edición de turnos, pacientes o recursos con modales interactivos (diferidos a `C-12`, `C-13` y `C-14`).
- Modificar el backend FastAPI existente ni sus esquemas de base de datos; el frontend actúa estrictamente como consumidor de `/api/v1`.
- Implementar registro público de usuarios (los usuarios son administrados por la clínica).

## Decisions

### 1. Stack Web: Vite + React 18+ + TypeScript (`DP-01`)
- **Decisión**: Utilizar Vite con React 18+ y TypeScript en modo estricto.
- **Razón**: Vite proporciona un tiempo de arranque y reemplazo de módulos en caliente (HMR) ultrarrápido sin sobrecarga de configuración. React 18 ofrece un ecosistema maduro y declarativo para componentes interactivos de gestión clínica. TypeScript garantiza la integridad de tipos compartidos con los contratos Pydantic del backend.
- **Alternativas descartadas**:
  - *Next.js / Remix*: Innecesario servidor Node.js y renderizado en servidor (SSR) para una aplicación de gestión interna autenticada (SaaS B2B).
  - *JavaScript puro / Vanilla SPA*: Falta de verificación de tipos estáticos en contratos de turnos, pacientes y estados.

### 2. Ruteo y RBAC: React Router DOM v6 con envoltura declarativa `ProtectedRoute`
- **Decisión**: Implementar `ProtectedRoute` que evalúe el estado del contexto de autenticación:
  - Si no está autenticado: redirige a `/login` preservando la ruta previa en el estado de navegación.
  - Si está autenticado pero su rol no está en la lista de `rolesPermitidos`: muestra un mensaje accesible de "Acceso Denegado / No Autorizado".
  - Si está autenticado y posee el rol adecuado: renderiza el componente hijo dentro del `Layout`.
- **Razón**: El enfoque declarativo centraliza la seguridad de navegación en la definición de rutas (`App.tsx`), evitando renderizados transitorios no autorizados o chequeos dispersos dentro de cada vista.
- **Alternativas descartadas**:
  - *Verificación imperativa en `useEffect` en cada página*: Proclive a omisiones accidentales y flashes de contenido antes de redirección.

### 3. Gestión de Estado: React Context (`AuthContext`) + `localStorage`
- **Decisión**: Centralizar el estado de sesión en un `AuthContext` nativo de React, persistiendo el token JWT y los datos del usuario en `localStorage`.
- **Razón**: La sesión de usuario es el único estado transversal global requerido en este nivel. Context API nativa es liviana, no introduce dependencias externas pesadas y simplifica el consumo mediante el hook personalizado `useAuth()`.
- **Alternativas descartadas**:
  - *Redux Toolkit / Zustand*: Sobredimensionado para almacenar únicamente el token y los datos de perfil de la sesión actual.
  - *Cookies HttpOnly*: Requerirían modificar la configuración de cookies y CORS en el backend FastAPI; el backend ya está especificado y probado con `Authorization: Bearer <token>` en header.

### 4. Cliente HTTP: Wrapper tipado sobre `fetch` nativo
- **Decisión**: Construir `api/cliente.ts` alrededor de la función `fetch` nativa del navegador, exponiendo métodos `get`, `post`, `put`, `delete`.
- **Razón**: `fetch` es un estándar de JavaScript moderno sin dependencias externas. El cliente inyecta automáticamente el token de autenticación cuando existe, configura `Content-Type: application/json`, parsea respuestas de error según el envelope `{"error": {"code": "...", "message": "..."}}`, y ante un status 401 limpia la sesión local y dispara una redirección controlada.
- **Alternativas descartadas**:
  - *Axios*: Agrega 30KB innecesarios al bundle para funcionalidades que el wrapper nativo cubre en menos de 80 líneas de código limpio.

### 5. Estilos y Diseño de Interfaz: CSS Moderno estructurado con variables de diseño clínico
- **Decisión**: Crear una hoja de estilos limpia (`src/index.css`) con variables CSS para la paleta de colores (azules médicos, neutros slate, estados verde/ámbar/rojo), tipografía e interlineado accesible, aplicando los principios de diseño sobrio de `emil-design-eng`.
- **Razón**: Mantiene la base de código libre de dependencias de UI pesadas, garantiza tiempos de carga instantáneos y proporciona total control sobre la accesibilidad y el espaciado visual de la interfaz clínica.
- **Alternativas descartadas**:
  - *Frameworks de componentes pesados (Material UI / Ant Design)*: Bloat en bundle y dificultad para personalizar comportamientos específicos de la agenda odontológica.

### 6. Suite de Pruebas: Vitest + @testing-library/react + jsdom
- **Decisión**: Configurar Vitest con Testing Library para ejecutar pruebas unitarias y de componentes directamente en el entorno de desarrollo de Vite.
- **Razón**: Vitest comparte la configuración de plugins y resolución de módulos de `vite.config.ts`, permitiendo pruebas ultrarrápidas sin configurar Babel ni transformadores Jest.

## Risks / Trade-offs

- **[Riesgo] Expiración silenciosa del token JWT en el cliente** → *Mitigación*: El cliente HTTP intercepta cualquier respuesta con código HTTP 401, purga el almacenamiento local (`localStorage.removeItem('token')`) y redirige automáticamente al usuario a `/login` con un mensaje indicando que su sesión expiró.
- **[Riesgo] Desincronización de contratos de datos entre API y Frontend** → *Mitigación*: Tipos de datos estrictos en `src/types/` espejando fielmente los esquemas Pydantic del backend (`Usuario`, `Rol`, `Turno`, `Paciente`, `Profesional`, `Sillon`, `Bloqueo`).
- **[Riesgo] Problemas de CORS durante el desarrollo local** → *Mitigación*: Configurar un proxy de desarrollo en `vite.config.ts` para que las peticiones a `/api/v1` sean redirigidas internamente a `http://localhost:8000`.

## Migration Plan

1. Crear la estructura del directorio `frontend/` con sus archivos de configuración (`package.json`, `tsconfig.json`, `vite.config.ts`, `.env.example`, `index.html`).
2. Instalar dependencias esenciales (`react`, `react-dom`, `react-router-dom`) y dependencias de desarrollo (`vite`, `typescript`, `@types/react`, `vitest`, `@testing-library/react`, `jsdom`).
3. Implementar los contratos de datos (`types/`) y el cliente HTTP (`api/cliente.ts`).
4. Implementar el contexto de autenticación (`context/AuthContext.tsx`) y los servicios de API (`api/auth.ts`, etc.).
5. Implementar los componentes estructurales (`Layout.tsx`, `Navbar.tsx`, `Sidebar.tsx`, `ProtectedRoute.tsx`).
6. Implementar las vistas base (`Login.tsx`, `Agenda.tsx`, `Pacientes.tsx`, `Recursos.tsx`, `Auditoria.tsx`) y configurar las rutas en `App.tsx`.
7. Crear y ejecutar las pruebas de frontend con `npm test`.
8. Verificar que la suite del backend siga pasando al 100% verde con `pytest` sin alteraciones.
