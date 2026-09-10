# GitHub PR Review Agent

Servicio FastAPI que recibe webhooks de pull requests de GitHub, ejecuta el agente de revisión y publica el resultado como un Check Run.

## Estructura

```text
app/
  main.py
  github_client.py
src/
  programmatic_agent_pr_reviewer.py
Dockerfile
docker-compose.yml
requirements.txt
.env.example
```

## Configuración

1. Copia `.env.example` como `.env` y configura las credenciales.
2. Usa un token de GitHub con `checks:write` y `contents:read`.
3. Conecta la implementación existente del agente en `src/programmatic_agent_pr_reviewer.py`.

## Ejecución local

```powershell
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Endpoints principales:

- `GET /health`
- `POST /github/webhook`

Configura en GitHub un webhook con tipo `application/json`, el secreto de `GITHUB_WEBHOOK_SECRET` y el evento `Pull requests`.

## Docker

```powershell
docker compose up --build
```
