# GitHub PR Review Agent

FastAPI service that accepts direct code review requests for GitHub pull requests and runs the PR review agent.

## Project structure

```text
src/
  agent_reviewer_server.py
  code_review_config.py
Dockerfile
docker-compose.yml
requirements.txt
majoya_test.py
.env.example
```

## Configuration

Create the runtime environment file from the example:

```powershell
Copy-Item .env.example .env
```

Update `.env` with a GitHub token that can read repository contents and pull requests, plus an OpenRouter API key and model:

```env
GITHUB_TOKEN=github_pat_or_token
OPEN_ROUTER_API_KEY=your_openrouter_api_key
MODEL=openai/gpt-4o-mini
```

`MODEL` must be a model identifier supported by OpenRouter, such as `openai/gpt-4o-mini`.

`.env` is ignored by Git. Do not commit tokens or API keys.

## Run locally

```powershell
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn src.agent_reviewer_server:app --host 127.0.0.1 --port 8000 --reload
```

The service is available at `http://localhost:8000`.

Main endpoints:

- `GET /health`
- `POST /review`

## Build and run with Docker Compose

Compose reads the variables from `.env`, builds the image, and publishes port `8000`:

```powershell
docker compose up --build -d
```

View logs:

```powershell
docker compose logs -f pr-review-agent
```

Stop and remove the container:

```powershell
docker compose down
```

## Build and run with Docker directly

```powershell
docker build -t github-pr-review-agent .
docker run --name github-pr-review-agent --env-file .env -p 8000:8000 github-pr-review-agent
```

## Test the service

### Health check

With the local server or container running:

```powershell
Invoke-RestMethod http://localhost:8000/health
curl.exe http://localhost:8000/health
```

The expected response is:

```json
{"status":"ok"}
```

### Python smoke check

Verify that the application and agent module can be imported:

```powershell
.venv/bin/python -c "from src.agent_reviewer_server import app; print(app.title)"
```

### Code review request

Start the service and send a review request with the test script:

```powershell
.venv/bin/python majoya_test.py jke94 weather-station 30
```

The script sends this JSON payload:

```json
{"owner":"jke94","repo":"weather-station","pr_number":30}
```

The service obtains the PR base and head from GitHub, runs the review, and returns the report in the `review` field.

## API documentation

FastAPI exposes interactive documentation at:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`
