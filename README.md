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
> **Nota:** Todos los 8 tests unitarios deben pasar en verde, validando el camino feliz, las excepciones de solapamiento por profesional y sillón, y los turnos contiguos bajo intervalos semiabiertos $[inicio, fin)$.

---

## Estructura del Repositorio

* `openspec/`: Estructura metodológica de OpenSpec con especificaciones vigentes (`specs/`) y cambios archivados (`changes/archive/`).
* `src/domain/`: Lógica de dominio puro en Python (modelos, servicios de validación y excepciones de negocio).
* `tests/`: Suite de pruebas unitarias automatizadas con `pytest`.
* `pytest.ini`: Configuración de resolución de módulos para ejecución directa.
* `requirements.txt`: Dependencias del entorno de testing (`pytest`, `pytest-cov`).

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
* Cristian Rodríguez
* Joseph Oliveros
