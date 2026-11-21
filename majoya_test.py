#!/usr/bin/env python3
"""Request a code review from the local review service."""

import argparse
import sys

import requests


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Request a code review for an existing GitHub pull request."
    )
    parser.add_argument("owner", help="GitHub repository owner")
    parser.add_argument("repo", help="GitHub repository name")
    parser.add_argument("pr_number", type=int, help="Pull request number")
    parser.add_argument(
        "--review-url",
        default="http://localhost:8000/review",
        help="Local review URL",
    )
    args = parser.parse_args()

    payload = {
        "owner": args.owner,
        "repo": args.repo,
        "pr_number": args.pr_number,
    }

    response = requests.post(
        args.review_url,
        json=payload,
        timeout=300,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError:
        print(f"{response.status_code} {response.text}", file=sys.stderr)
        raise

    result = response.json()
    print(result["review"])


if __name__ == "__main__":
    main()
