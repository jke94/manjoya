# GitHub PR Review Agent

FastAPI service that receives GitHub pull request webhooks, runs the PR review agent, and publishes the result as a GitHub Check Run.

## Project structure

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

## Configuration

Create the runtime environment file from the example:

```powershell
Copy-Item .env.example .env
```

Update `.env` with a GitHub token that has `checks:write` and `contents:read` permissions, plus the Ollama connection settings:

```env
GITHUB_WEBHOOK_SECRET=replace_with_a_strong_secret
GITHUB_TOKEN=github_pat_or_token
OLLAMA_HOST=https://your-ollama-endpoint.example
OLLAMA_API_KEY=your_ollama_api_key
MODEL=qwen2.5:7b
```

`.env` is ignored by Git. Do not commit tokens or API keys.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The service is available at `http://localhost:8000`.

Main endpoints:

- `GET /health`
- `POST /github/webhook`

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
python -c "from app.main import app; from src.programmatic_agent_pr_reviewer import review_branch; print(app.title)"
```

### GitHub webhook

Configure a webhook in the target repository:

1. Open **Settings** > **Webhooks** > **Add webhook**.
2. Set the payload URL to `https://your-domain.example/github/webhook`.
3. Set **Content type** to `application/json`.
4. Set the secret to the value of `GITHUB_WEBHOOK_SECRET`.
5. Select **Pull requests** events.

The service reviews pull requests when the action is `opened`, `reopened`, or `synchronize`. Use GitHub's **Recent Deliveries** page to send a test delivery and inspect the response. A successful review creates a `PR Review Agent` Check Run on the pull request.

## API documentation

FastAPI exposes interactive documentation at:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`
