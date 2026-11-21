#!/usr/bin/env python3
"""FastAPI server that reviews a GitHub pull request with OpenRouter."""

import base64
import json
import os
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.code_review_config import SYSTEM_PROMPT, TOOLS

load_dotenv(override=True)

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")
MODEL = os.getenv("MODEL")
MAX_ITERATIONS = 20

app = FastAPI(
    title="GitHub PR Code Review Agent",
    description="Direct code review API for GitHub pull requests using OpenRouter.",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "reviews",
            "description": "Pull request code review operations.",
        },
        {
            "name": "health",
            "description": "Service availability checks.",
        },
    ],
)


def github_headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def github_get(url: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(
        url,
        headers=github_headers(),
        params=params,
        timeout=60,
    )
    if response.status_code == 404:
        raise ValueError(f"GitHub resource not found: {url}")
    response.raise_for_status()
    return response.json()


def get_comparison(owner: str, repo: str, base: str, head: str) -> dict[str, Any]:
    data = github_get(
        f"{GITHUB_API}/repos/{owner}/{repo}/compare/{base}...{head}"
    )
    return {
        "status": data.get("status"),
        "ahead_by": data.get("ahead_by"),
        "behind_by": data.get("behind_by"),
        "total_commits": data.get("total_commits"),
        "commits": [
            {
                "sha": commit["sha"][:8],
                "message": commit["commit"]["message"].split("\n")[0],
            }
            for commit in data.get("commits", [])
        ],
        "files": [
            {
                "filename": file["filename"],
                "status": file["status"],
                "additions": file.get("additions", 0),
                "deletions": file.get("deletions", 0),
                "patch": file.get("patch"),
            }
            for file in data.get("files", [])
        ],
    }


def get_pr_files(owner: str, repo: str, pr_number: int) -> dict[str, Any]:
    files = github_get(
        f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files"
    )
    pr = github_get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}")
    return {
        "title": pr.get("title"),
        "body": pr.get("body"),
        "base": pr["base"]["ref"],
        "head": pr["head"]["sha"],
        "files": [
            {
                "filename": file["filename"],
                "status": file["status"],
                "additions": file.get("additions", 0),
                "deletions": file.get("deletions", 0),
                "patch": file.get("patch"),
            }
            for file in files
        ],
    }


def get_file_content(owner: str, repo: str, path: str, ref: str) -> str:
    data = github_get(
        f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
        params={"ref": ref},
    )
    if data.get("encoding") == "base64":
        return base64.b64decode(data["content"]).decode(
            "utf-8", errors="replace"
        )
    return data.get("content", "")


def open_router_chat(
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
            "temperature": 0.1,
        },
        timeout=180,
    )
    if not response.ok:
        raise RuntimeError(
            f"OpenRouter API error ({response.status_code}): {response.text}"
        )
    return response.json()["choices"][0]["message"]


def tool_result_content(result: Any) -> str:
    content = (
        json.dumps(result, indent=2, ensure_ascii=False)
        if isinstance(result, (dict, list))
        else str(result)
    )
    return content[:25000] + "\n\n... [truncated]" if len(content) > 25000 else content


def review_branch(
    owner: str,
    repo: str,
    base_branch: str,
    head_branch: str,
    pr_number: int,
) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Review pull request #{pr_number} from `{head_branch}` against "
                f"`{base_branch}` in `{owner}/{repo}`. Always call get_comparison "
                "first and return the requested review format."
            ),
        },
    ]

    for _ in range(MAX_ITERATIONS):
        message = open_router_chat(messages)
        assistant_message: dict[str, Any] = {"role": "assistant"}

        if message.get("content"):
            assistant_message["content"] = message["content"]

        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            assistant_message["tool_calls"] = tool_calls
        messages.append(assistant_message)

        if not tool_calls:
            return message.get("content") or ""

        for tool_call in tool_calls:
            call_id = tool_call["id"]
            function = tool_call["function"]
            name = function["name"]
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments)

            try:
                if name == "get_comparison":
                    result = get_comparison(owner, repo, arguments["base"], arguments["head"])
                elif name == "get_pr_files":
                    result = get_pr_files(owner, repo, arguments["pr_number"])
                elif name == "get_file_content":
                    result = get_file_content(owner, repo, arguments["path"], arguments["ref"])
                else:
                    result = f"Unknown tool: {name}"
            except Exception as exc:
                result = f"Error in tool {name}: {exc}"

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": tool_result_content(result),
                }
            )

    raise RuntimeError(
        f"Maximum agent iterations reached ({MAX_ITERATIONS})."
    )


class ReviewRequest(BaseModel):
    owner: str = Field(
        description="GitHub repository owner.",
        examples=["jke94"],
    )
    repo: str = Field(
        description="GitHub repository name.",
        examples=["weather-station"],
    )
    pr_number: int = Field(
        gt=0,
        description="Pull request number.",
        examples=[30],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "owner": "jke94",
                    "repo": "weather-station",
                    "pr_number": 30,
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])


class ReviewResponse(BaseModel):
    status: str = Field(examples=["ok"])
    pr: int = Field(description="Reviewed pull request number.", examples=[30])
    review: str = Field(description="Markdown code review report.")


class ErrorResponse(BaseModel):
    detail: str = Field(description="Human-readable error detail.")


@app.get(
    "/health",
    tags=["health"],
    summary="Check service health",
    response_model=HealthResponse,
)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post(
    "/review",
    tags=["reviews"],
    summary="Review a GitHub pull request",
    response_model=ReviewResponse,
    responses={
        500: {
            "model": ErrorResponse,
            "description": "GitHub, OpenRouter, or configuration error.",
        }
    },
)
def review_pull_request(request: ReviewRequest) -> ReviewResponse:
    if not GITHUB_TOKEN:
        raise HTTPException(status_code=500, detail="Missing GITHUB_TOKEN")
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="Missing OPEN_ROUTER_API_KEY")
    if not MODEL:
        raise HTTPException(status_code=500, detail="Missing MODEL")

    try:
        pr = github_get(
            f"{GITHUB_API}/repos/{request.owner}/{request.repo}/pulls/{request.pr_number}"
        )
        report = review_branch(
            owner=request.owner,
            repo=request.repo,
            base_branch=pr["base"]["ref"],
            head_branch=pr["head"]["sha"],
            pr_number=request.pr_number,
        )
        return ReviewResponse(
            status="ok",
            pr=request.pr_number,
            review=report,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
