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

## ✅ Requisitos

- Python 3.12 o superior
- pip
- Acceso a Azure SQL Server (el firewall debe permitir la IP desde la que se ejecuta Alembic o la API)

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

En Azure App Service, define las mismas variables `SQLSERVER_*` como Application Settings. `pymssql` se instala con el resto de dependencias; no requiere driver ODBC en el runtime.

## 🔌 Endpoints

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/health` | Estado del servicio |

Documentación interactiva:

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## 🧪 Pruebas

Con el entorno virtual activado:

```bash
pytest
```

## ☁️ Despliegue

Al hacer push a `main`, GitHub Actions construye la aplicación con Python 3.12 y la publica en Azure App Service (`bpo-platform-deploy`) con:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
