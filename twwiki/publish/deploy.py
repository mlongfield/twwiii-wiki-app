"""Start the GitHub Actions deploy workflow for a build."""

from __future__ import annotations

import json

from . import PublishError
from .stores import HttpPost

GITHUB_API = "https://api.github.com"

_AFTER = ("The site still shows the previous pages. Fix the cause, then run "
          "`uv run python -m twwiki.publish --deploy-only`.")


def dispatch_deploy(post: HttpPost, *, repo: str, workflow: str, ref: str, build_id: str, token: str) -> str:
    url = f"{GITHUB_API}/repos/{repo}/actions/workflows/{workflow}/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "twwiki-publish",
    }
    body = json.dumps({"ref": ref, "inputs": {"build_id": build_id}}).encode("utf-8")
    try:
        status = post(url, headers, body)
    except OSError as e:
        raise PublishError(f"could not reach GitHub to start the deploy ({e}). {_AFTER}") from e
    if status in (200, 204):
        return f"https://github.com/{repo}/actions/workflows/{workflow}"
    if status in (401, 403):
        reason = "the token in TWWIKI_GITHUB_TOKEN was rejected or lacks Actions read and write on this repository"
    elif status == 404:
        reason = f"GitHub found no workflow {workflow} on {ref} in {repo}, or the token cannot see the repository"
    else:
        reason = f"GitHub answered HTTP {status}"
    raise PublishError(f"deploy dispatch failed (HTTP {status}): {reason}. {_AFTER}")
