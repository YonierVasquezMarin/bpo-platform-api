# 🚀 BPO Platform API

API orquestadora de la solución agéntica BPO. Expone servicios HTTP para coordinar los flujos de la plataforma.

## 🛠️ Tecnologías

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-499848)
![Pydantic](https://img.shields.io/badge/Pydantic_Settings-E92063?logo=pydantic&logoColor=white)
![httpx](https://img.shields.io/badge/httpx-0052CC)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?logo=pytest&logoColor=white)
![Azure](https://img.shields.io/badge/Azure_App_Service-0078D4?logo=microsoftazure&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white)

## ✅ Requisitos

- Python 3.12 o superior
- pip

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

4. (Opcional) Crear un archivo `.env` en la raíz del proyecto. Si no existe, se usan los valores por defecto:

```env
APP_NAME=bpo-platform-api
APP_VERSION=0.1.0
ENVIRONMENT=development
```

5. Iniciar el servidor:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

En Cursor o VS Code también se puede usar la tarea **Iniciar API (uvicorn)**.

La API queda disponible en `http://127.0.0.1:8000`.

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
