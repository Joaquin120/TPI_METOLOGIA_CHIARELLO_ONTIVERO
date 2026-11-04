# Sistema de Gestión de Turnos Odontológicos

Este repositorio contiene la lógica de dominio para la gestión de turnos odontológicos, resolviendo la doble restricción física de disponibilidad simultánea de profesionales y sillones/boxes. El proyecto fue especificado y construido bajo la metodología **Spec-Driven Development (SDD)** con **Active Stack**.

---

## Requisitos Previos

* Python 3.11 o superior.
* Git.

---

## Instalación y Ejecución de Tests

Para clonar el repositorio y ejecutar la suite de pruebas desde cero, seguí estos pasos exactos en tu terminal:

### 1. Clonar el repositorio
```bash
git clone [https://github.com/Joaquin120/TPI_CHIARELLO_OLIVEROS_ONTIVERO_RODRIGUEZ_METODOLOGIA1.git](https://github.com/Joaquin120/TPI_CHIARELLO_OLIVEROS_ONTIVERO_RODRIGUEZ_METODOLOGIA1.git)
cd TPI_CHIARELLO_OLIVEROS_ONTIVERO_RODRIGUEZ_METODOLOGIA1/turnos-odontologia
```

### 2. Crear y activar el entorno virtual
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Ejecutar la suite de pruebas
```bash
pytest -v
```
o
```bash
python3 -m pytest -v
```
> **Nota:** la suite completa debe pasar en verde, validando el camino feliz, las excepciones de solapamiento por profesional y sillón, los turnos contiguos bajo intervalos semiabiertos $[inicio, fin)$, la persistencia SQLite, el desacople del dominio y los endpoints de la API.

---

## API REST (FastAPI)

La capa HTTP vive en `backend/src/api/` y expone un slice vertical bajo `/api/v1`:
`health`, alta de turnos y listado por tenant. **La API delega la doble validación
(profesional y sillón) y las transiciones en el dominio**; no reimplementa reglas.
El dominio (`backend/src/domain/`) no importa FastAPI, Pydantic, SQLite ni
repositorios (hay un guard test que lo verifica).

### Arranque

Desde `backend/`, con el entorno virtual activado:

```bash
# 1. Dependencias
pip install -r requirements.txt

# 2. (Opcional) migrar y sembrar datos sintéticos: 1 tenant, 2 profesionales, 2 sillones
python -c "from src.api.app import create_app; create_app(sembrar=True)"

# 3. Levantar la API (factoría: no hay `app` global de módulo)
python -m uvicorn src.api.app:create_app --factory
```

La base por defecto es `turnos.db` en el directorio de trabajo. Se puede apuntar a
otra ruta con la variable de entorno `TURNO_DB_PATH` (configuración, sin secretos).
La factoría `create_app(*, ruta_db=None, tenant_por_defecto=None, sembrar=False)`
migra al arrancar y siembra solo si `sembrar=True`.

### Tenant

Toda operación de negocio opera dentro de un tenant resuelto explícitamente, con
esta precedencia:

1. Encabezado `X-Tenant-ID` (entero).
2. `tenant_por_defecto` pasado a `create_app(...)`.
3. Variable de entorno `TURNO_TENANT_ID` (leída en la factoría).
4. Si no se resuelve, o el id no existe en la tabla `tenant` → `400 TENANT_NO_RESUELTO`.

> El header es **provisorio, solo desarrollo/pruebas** y no es un mecanismo de
> seguridad: `C-04` lo reemplazará por el tenant de la sesión/JWT.

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/health` | Disponibilidad; no requiere tenant ni consulta datos de negocio. |
| `POST` | `/api/v1/turnos` | Alta de turno; responde `201` con el turno creado. |
| `GET` | `/api/v1/turnos` | Listado de turnos del tenant resuelto (sin filtros ni paginación en C-03). |

El contrato usa **nombres** de recurso (`paciente`, `profesional`, `sillon`) porque
el dominio resuelve por nombre dentro del tenant; migrar a `*_id` queda para
`DP-06`/`C-05`.

```bash
# Alta (requiere datos sembrados y un tenant válido, p. ej. 1)
curl -X POST http://127.0.0.1:8000/api/v1/turnos \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: 1" \
  -d '{"paciente":"Paciente Ficticio","profesional":"Dr. Ejemplo","sillon":"Sillón 1","fecha":"2026-11-01","hora_inicio":"10:00","hora_fin":"10:30"}'

# Listado del tenant
curl http://127.0.0.1:8000/api/v1/turnos -H "X-Tenant-ID: 1"
```

Respuesta de turno (alta y cada ítem del listado):

```json
{
  "id": 1,
  "paciente": "Paciente Ficticio",
  "profesional": "Dr. Ejemplo",
  "sillon": "Sillón 1",
  "fecha": "2026-11-01",
  "hora_inicio": "10:00",
  "hora_fin": "10:30",
  "estado": "CONFIRMADO"
}
```

### Contrato de error

Todas las fallas usan el mismo envelope:

```json
{ "error": { "code": "SOLAPAMIENTO_PROFESIONAL", "message": "..." } }
```

| Origen | HTTP | `error.code` |
|---|---|---|
| Profesional ocupado | `409` | `SOLAPAMIENTO_PROFESIONAL` |
| Sillón ocupado | `409` | `SOLAPAMIENTO_SILLON` |
| Transición inválida | `409` | `TRANSICION_INVALIDA` |
| Cuerpo/parámetros inválidos | `422` | `VALIDACION` |
| Tenant no resoluble o inexistente | `400` | `TENANT_NO_RESUELTO` |

`extra="forbid"` impide enviar `tenant_id` en el cuerpo. No se valida
`hora_inicio < hora_fin` (pertenece a `RP-01`, abierta).

---

## Estructura del Repositorio

* `openspec/`: Estructura metodológica de OpenSpec con especificaciones vigentes (`specs/`) y cambios archivados (`changes/archive/`).
* `backend/src/domain/`: Lógica de dominio puro en Python (modelos, puertos, servicios y excepciones de negocio).
* `backend/src/repositories/`: Adaptadores de persistencia (`PuertoTurnos` en memoria y SQLite por tenant).
* `backend/src/infrastructure/`: Conexión SQLite, migraciones, configuración y seed sintético.
* `backend/src/api/`: Capa HTTP/JSON (factoría FastAPI, routers, esquemas Pydantic, dependencias y handlers de error).
* `backend/tests/`: Suite de pruebas automatizadas con `pytest` (dominio, persistencia real y API con `TestClient`).
* `backend/pytest.ini`: Configuración de resolución de módulos para ejecución directa.
* `backend/requirements.txt`: Dependencias de testing y de la API (`pytest`, `pytest-cov`, `fastapi`, `pydantic`, `httpx`, `uvicorn`).

---

## Integración MCP: Filesystem Server

### Propósito

Integrar el servidor MCP **Filesystem** (`@modelcontextprotocol/server-filesystem`) para la **lectura e inspección estructurada de archivos locales** — `knowledge-base/`, `openspec/specs/` y `openspec/changes/archive/` — de forma verificable, **evitando alucinaciones** sobre contenido de rutas, specs y reglas que el agente no abrió realmente.

### Requisitos

* **Node.js v18 o superior** (verificado con `node --version`).
* **`npx`** disponible en el PATH (se instala junto con Node).
* Sin credenciales, tokens ni variables de entorno: configuración **sin secretos**.

### Configuración del cliente (JSON)

Agregá este bloque a la configuración del cliente MCP (OpenCode: `opencode.json`; el formato es análogo en otros clientes). La raíz es la **ruta absoluta del repositorio** — fuera de ella el servidor deniega el acceso:

```json
{
  "mcp": {
    "filesystem": {
      "type": "local",
      "command": [
        "npx",
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/home/joaquin/Documentos/TPI_CHIARELLO_OLIVEROS_ONTIVERO_RODRIGUEZ_METODOLOGIA1"
      ],
      "environment": {},
      "enabled": true
    }
  }
}
```

> **Nota de seguridad**: el servidor queda acotado a la raíz del repo, se usa en **modo solo lectura** (solo `list_directory`, `read_file`, `get_file_info`) y el proyecto no contiene datos sensibles (regla dura 3: solo datos sintéticos).

### Verificación de conexión (paso a paso)

1. Reiniciá el cliente MCP para que cargue la nueva configuración.
2. Comprobá que la herramienta `list_directory` esté disponible en la lista de tools del cliente.
3. Ejecutá `list_directory` con el argumento `path` apuntando al archivo vivo de cambios archivados:
   ```json
   { "path": "/home/joaquin/Documentos/TPI_CHIARELLO_OLIVEROS_ONTIVERO_RODRIGUEZ_METODOLOGIA1/openspec/changes/archive" }
   ```
4. **Resultado esperado**: el servidor devuelve la entrada `2026-10-15-crear-turno-sin-solapamientos/` (change archivado). Si aparece esa entrada, la conexión está verificada.
5. Como contraste negativo, pedí una ruta **fuera de la raíz** (ej. `/etc`): el servidor debe rechazarla con error de acceso — eso confirma que el confinamiento funciona.

### Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `npx: command not found` o error `ENOENT` | Node.js no instalado o PATH incompleto | Instalar Node v18+ y reabrir la terminal; verificar con `node --version` y `which npx` |
| `EACCES` / permiso denegado al ejecutar `npx` | Caché de npm con permisos ajenos (gestión por nvm, instalación previa con sudo) | No usar `sudo npm`; corregir permisos de la caché con `npm config get cache` y `chown -R` sobre ese directorio, o reinstalar Node con nvm |
| Error de acceso a un archivo aunque esté dentro del repo | **Ruta relativa** o ruta errónea | Usar siempre **ruta absoluta** completa; el servidor no resuelve rutas relativas ni `~` |
| El servidor no aparece en el cliente | Configuración en el archivo equivocado o cliente sin reiniciar | Verificar que el JSON esté en la config activa del cliente y reiniciar la sesión |
| Timeout en la primera llamada | `npx` descarga el paquete la primera vez | Esperar la descarga o pre-cachear con `npx -y @modelcontextprotocol/server-filesystem --help` |

---

## Integrantes del Equipo

* Joaquín Chiarello
* Santiago Ontivero
