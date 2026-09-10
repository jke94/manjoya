import hashlib
import hmac
import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request

from src.programmatic_agent_pr_reviewer import OllamaProvider, review_branch

app = FastAPI(title="GitHub PR Review Agent")

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
MODEL = os.getenv("MODEL", "qwen2.5:7b")


def verify_signature(payload: bytes, signature: str | None) -> bool:
    if not GITHUB_WEBHOOK_SECRET:
        return True
    if not signature:
        return False

    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def create_ollama_provider() -> OllamaProvider:
    return OllamaProvider(
        base_url=OLLAMA_HOST,
        default_model=MODEL,
        api_key=OLLAMA_API_KEY,
        timeout=180,
    )


def github_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def get_pr_head_sha(owner: str, repo: str, pr_number: int) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
            headers=github_headers(),
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["head"]["sha"]


async def create_github_check(
    owner: str, repo: str, pr_number: int, conclusion: str, summary: str
) -> None:
    payload = {
        "name": "PR Review Agent",
        "head_sha": await get_pr_head_sha(owner, repo, pr_number),
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": "Git Branch Review",
            "summary": summary[:65535],
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/check-runs",
            headers=github_headers(),
            json=payload,
            timeout=60,
        )
        response.raise_for_status()


@app.post("/github/webhook")
async def github_webhook(request: Request) -> dict[str, Any]:
    raw = await request.body()
    if not verify_signature(raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    action = payload.get("action")
    if action not in {"opened", "reopened", "synchronize"}:
        return {"status": "ignored", "action": action}

    pr = payload.get("pull_request")
    repository = payload.get("repository")
    if not pr or not repository:
        return {"status": "ignored", "reason": "Missing PR or repository payload"}

    owner = repository["owner"]["login"]
    repo = repository["name"]
    pr_number = pr["number"]

    try:
        report = review_branch(
            llm_provider=create_ollama_provider(),
            owner=owner,
            repo=repo,
            base_branch=pr["base"]["ref"],
            feature_branch=pr["head"]["ref"],
            pr_number=pr_number,
        )
        await create_github_check(owner, repo, pr_number, "success", report)
        return {"status": "ok", "pr": pr_number, "summary": "Review completed"}
    except Exception as exc:
        try:
            await create_github_check(
                owner, repo, pr_number, "failure", f"PR review failed: {exc}"
            )
        finally:
            raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
