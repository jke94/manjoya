# GitHub PR Review Agent

FastAPI service that performs pull request code reviews using GitHub as the repository source and OpenRouter as the LLM provider.

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

## Environment configuration

Create `.env` from the example:

```bash
cp .env.example .env
```

Configure:

```env
GITHUB_TOKEN=github_pat_or_token
OPEN_ROUTER_API_KEY=your_openrouter_api_key
MODEL=openai/gpt-4o-mini
```

- `GITHUB_TOKEN`: classic or fine-grained token with read access to repository contents and pull requests.
- `OPEN_ROUTER_API_KEY`: OpenRouter API key.
- `MODEL`: OpenRouter model identifier, for example `openai/gpt-4o-mini`.

`.env` is ignored by Git. Do not commit tokens or API keys.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn src.agent_reviewer_server:app --host 127.0.0.1 --port 8000 --reload
```

The service is available at `http://localhost:8000`.

Endpoints:

- `GET /health`: service health.
- `POST /review`: code review request.
- `GET /docs`: interactive Swagger documentation.
- `GET /redoc`: ReDoc documentation.
- `GET /openapi.json`: OpenAPI 3 specification.

## Build and run with Docker Compose

Compose reads `.env`, builds the image, publishes port `8000`, and enables a container health check:

```bash
docker compose up --build -d
```

View logs or stop the service:

```bash
docker compose logs -f pr-review-agent
docker compose down
```

## Build and run with Docker directly

```bash
docker build -t github-pr-review-agent .
docker run --name github-pr-review-agent --env-file .env -p 8000:8000 github-pr-review-agent
```

## Test the service

### Health check

With the local server or container running:

```bash
curl http://localhost:8000/health
```

The expected response is:

```json
{"status":"ok"}
```

### Python smoke check

Verify that the server module and FastAPI application can be imported:

```bash
.venv/bin/python -c "from src.agent_reviewer_server import app; print(app.title)"
```

### Code review request

Start the service and send a review request with the test script:

```bash
.venv/bin/python majoya_test.py jke94 weather-station 30
```

The script sends this JSON payload:

```json
{
  "owner": "jke94",
  "repo": "weather-station",
  "pr_number": 30
}
```

The service obtains the pull request base and head references from GitHub, runs the review through OpenRouter, and returns the Markdown report in `review`.

Example response:

```json
{
  "status": "ok",
  "pr": 30,
  "review": "# Code review report"
}
```
