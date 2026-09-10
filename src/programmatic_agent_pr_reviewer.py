"""PR review agent integration point.

Replace these stubs with the existing agent implementation. The public
functions below match the FastAPI webhook contract.
"""

from dataclasses import dataclass


@dataclass
class OllamaProvider:
    base_url: str
    default_model: str
    api_key: str = ""
    timeout: int = 180


def review_branch(
    llm_provider: OllamaProvider,
    owner: str,
    repo: str,
    base_branch: str,
    feature_branch: str,
    pr_number: int,
) -> str:
    raise NotImplementedError(
        "Connect the existing programmatic-agent-PR-reviewer implementation."
    )
