# 🚀 BPO Platform API

API orquestadora de la solución agéntica BPO. Expone servicios HTTP para coordinar los flujos de la plataforma.

## 🛠️ Tecnologías

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-499848)
![Pydantic](https://img.shields.io/badge/Pydantic_Settings-E92063?logo=pydantic&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?logo=sqlalchemy&logoColor=white)
![pymssql](https://img.shields.io/badge/pymssql-FreeTDS-2F4F4F)
![Alembic](https://img.shields.io/badge/Alembic-migrations-8B4513)
![SQL Server](https://img.shields.io/badge/Azure_SQL-CC2927?logo=microsoftsqlserver&logoColor=white)
![httpx](https://img.shields.io/badge/httpx-0052CC)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?logo=pytest&logoColor=white)
![Azure](https://img.shields.io/badge/Azure_App_Service-0078D4?logo=microsoftazure&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white)

## 🏗️ Arquitectura

Vista general de la solución: la API orquesta los flujos de ingestión de conocimiento y de agente conversacional sobre Azure.

![Arquitectura de BPO Platform](architecture.png)

## ✅ Requisitos

- Python 3.12 o superior
- pip
- Acceso a Azure SQL Server (el firewall debe permitir la IP desde la que se ejecuta Alembic o la API)

## 🧩 Extensiones recomendadas (Cursor / VS Code)

Se recomienda instalar estas extensiones:

- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) (`ms-python.python`)
- [Python Debugger](https://marketplace.visualstudio.com/items?itemName=ms-python.debugpy) (`ms-python.debugpy`)
- [GitHub Actions](https://marketplace.visualstudio.com/items?itemName=github.vscode-github-actions) (`github.vscode-github-actions`)

## ▶️ Arranque local

1. Clonar el repositorio y entrar al directorio del proyecto:

```bash
git clone <url-del-repositorio>
cd bpo-platform-api
```

2. Crear y activar un entorno virtual.

En Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

En Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Crear un archivo `.env` en la raíz del proyecto. Si no existe, se usan valores por defecto (no conectan a Azure):

```env
APP_NAME=bpo-platform-api
APP_VERSION=0.1.0
ENVIRONMENT=development

SQLSERVER_SERVER=tu-servidor.database.windows.net
SQLSERVER_DATABASE=nombre_bd
SQLSERVER_USER=usuario_sql
SQLSERVER_PASSWORD=********

ENCRYPTION_KEY=********
ENCRYPTION_SALT=********

JWT_SECRET_KEY=********
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
```

5. Iniciar el servidor:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

En Cursor o VS Code también se puede usar la tarea **Iniciar API (uvicorn)**.

La API queda disponible en `http://127.0.0.1:8000`.

## 🗄️ Base de datos y migraciones

El esquema se versiona con **Alembic**. El comando que **sube** los modelos a Azure SQL Server es:

```bash
alembic upgrade head
```

Antes de ejecutarlo:

- Completa las variables `SQLSERVER_*` en `.env`
- En Azure SQL, agrega tu IP de desarrollo en el firewall
- El usuario SQL debe poder crear tablas (por ejemplo `db_ddladmin`)

La conexión usa **pymssql** (incluido en `requirements.txt`). No hace falta instalar ODBC ni otros binarios en local ni en Azure.

Flujo habitual cuando cambia un modelo ORM:

1. Editar el modelo en `app/models`
2. Generar la migración: `alembic revision --autogenerate -m "descripcion del cambio"`
3. Revisar el archivo creado en `alembic/versions`
4. Aplicar: `alembic upgrade head`

Otros comandos:

```bash
# Revertir la última migración
alembic downgrade -1

# Consultar la versión aplicada
alembic current

# Ver el historial de migraciones
alembic history
```

Las migraciones **no** se ejecutan al arrancar Uvicorn. Hay que lanzar `alembic upgrade head` de forma explícita contra la base deseada.

En Azure App Service, define las mismas variables `SQLSERVER_*`, `ENCRYPTION_*` y `JWT_*` como Application Settings. `pymssql` se instala con el resto de dependencias; no requiere driver ODBC en el runtime.

## 🔌 Endpoints

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/api/health` | Estado del servicio |
| `POST` | `/api/auth/login` | Autenticación con email y contraseña; retorna un JWT |

Documentación interactiva:

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## 🧪 Pruebas

Con el entorno virtual activado:

```bash
pytest
```

## 🧯 Solución de problemas

### 🖥️ Entorno local

---

#### ❌ El entorno virtual no se activa en PowerShell

- **Síntoma:** `.\.venv\Scripts\Activate.ps1` falla con un mensaje de política de ejecución (`execution policy`).
- **Solución:** permite scripts para tu usuario y vuelve a activar el entorno:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Si el prompt no muestra `(.venv)`, las dependencias se instalarán en el Python global y luego fallarán `uvicorn`, `alembic` o `pytest`.

---

#### ❌ `python` o `pip` no se reconocen

- **Síntoma:** `python: command not found` o `No se encontró Python`.
- **Solución:** usa Python 3.12 o superior y, en Windows, prueba `py -3.12 -m venv .venv`. Después instala dependencias **dentro** del entorno activado:

```bash
python -m pip install -r requirements.txt
```

---

#### ❌ `ModuleNotFoundError` al arrancar o al correr pytest

- **Síntoma:** falta `fastapi`, `uvicorn`, `pymssql`, `alembic` u otro paquete de `requirements.txt`.
- **Solución:** activa `.venv` e instala de nuevo `pip install -r requirements.txt`. Ejecuta los comandos desde la raíz del repositorio (`bpo-platform-api`), no desde un subdirectorio.

---

#### ❌ Puerto 8000 ocupado

- **Síntoma:** `Address already in use` o `error while attempting to bind on address ('127.0.0.1', 8000)`.
- **Solución:** cierra el proceso que ya usa el puerto o arranca en otro:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

---

#### ❌ La tarea de Cursor / VS Code no arranca la API

- **Síntoma:** la tarea **Iniciar API (uvicorn)** no encuentra `.venv\Scripts\python.exe`.
- **Solución:** crea el entorno en la raíz del proyecto (`python -m venv .venv`) e instala dependencias. La tarea usa esa ruta de forma fija.

### 🔑 Variables de entorno

---

#### ❌ Falta `JWT_SECRET_KEY`

- **Síntoma:** el primer `POST /api/auth/login` responde 500. En consola aparece `ValueError: JWT_SECRET_KEY debe estar definida en .env`.
- **Solución:** copia `.env.example` a `.env` y define `JWT_SECRET_KEY` con un valor no vacío. Reinicia Uvicorn para que recargue la configuración.

---

#### ❌ Faltan `ENCRYPTION_KEY` o `ENCRYPTION_SALT`

- **Síntoma:** igual que el anterior, pero el error menciona las claves de cifrado.
- **Solución:** define `ENCRYPTION_KEY` y `ENCRYPTION_SALT` en `.env` (puedes partir de `.env.example`). Deben ser las **mismas** claves con las que se cifraron las contraseñas guardadas en `users.password`. Si cambian, el login devolverá 401.

### 🔐 Autenticación

---

#### ❌ Login 401 — Credenciales inválidas

- **Causas habituales:** email o contraseña incorrectos; el usuario no existe en Azure SQL; las claves `ENCRYPTION_*` locales no coinciden con las usadas al cifrar el password en base de datos.
- **Solución:** verifica el registro en la tabla `users`, cifra de nuevo la contraseña con la tarea **Cifrar contraseña** (o `python scripts/encrypt_password.py encrypt "<texto>"`) y actualiza `users.password` con el valor generado.

---

#### ❌ Login 403 — El usuario está inactivo

- **Síntoma:** email y contraseña son correctos, pero `is_active` está en `0`.
- **Solución:** activa el usuario en SQL:

```sql
UPDATE users SET is_active = 1 WHERE email = 'usuario@ejemplo.com';
```

---

#### ❌ Login 422 — Payload inválido

- **Síntoma:** el cuerpo no pasa validación de Pydantic (`email` inválido o `password` vacío).
- **Solución:** envía JSON con un email válido y una contraseña de 1 a 128 caracteres:

```json
{
  "email": "usuario@ejemplo.com",
  "password": "tu-password"
}
```

### 🗄️ Base de datos y Azure

---

#### ❌ No hay conexión a Azure SQL

- **Síntoma:** `login timeout expired`, `Adaptive Server connection failed`, o `Client with IP address ... is not allowed to access the server`. Alembic también puede quedarse en timeout.
- **Solución:**
  1. Completa `SQLSERVER_SERVER`, `SQLSERVER_DATABASE`, `SQLSERVER_USER` y `SQLSERVER_PASSWORD` en `.env`
  2. En Azure SQL, agrega tu IP pública al firewall
  3. Confirma que el servidor es el FQDN (`*.database.windows.net`) y que el usuario SQL es correcto
  4. Prueba de nuevo `alembic current` o `alembic upgrade head`

---

#### ❌ `alembic upgrade head` falla

- **Síntoma:** error de permisos al crear tablas, o consultas posteriores fallan porque no existe `users`.
- **Solución:** el usuario SQL necesita poder crear objetos (por ejemplo `db_ddladmin`). Las migraciones **no** corren al iniciar Uvicorn; hay que ejecutar:

```bash
alembic upgrade head
```

Si la base ya tiene tablas creadas a mano, no fuerces un `upgrade` a ciegas: revisa `alembic current` y `alembic history` antes de aplicar cambios.

---

#### ❌ App Service: el login falla o la app no arranca

- **Síntoma:** 500 al autenticar, o el sitio no responde tras el deploy.
- **Solución:** en Application Settings del App Service define las mismas variables que en `.env` (`SQLSERVER_*`, `ENCRYPTION_*`, `JWT_*`). El firewall de Azure SQL debe permitir los IPs de salida del App Service. Recuerda aplicar migraciones contra esa base (`alembic upgrade head`) antes de usar `/api/auth/login`.

## ☁️ Despliegue

Al hacer push a `main`, GitHub Actions construye la aplicación con Python 3.12 y la publica en Azure App Service (`bpo-platform-deploy`) con:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
