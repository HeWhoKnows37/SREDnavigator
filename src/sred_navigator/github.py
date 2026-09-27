from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from .models import CommitInput, GitHubRequest, JiraTicketInput, NarrativeRequest


GITHUB_API = "https://api.github.com"


def _get(path: str, token: Optional[str], params: Dict[str, Any]) -> Any:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(f"{GITHUB_API}{path}", headers=headers, params=params, timeout=30)
    if not response.ok:
        try:
            detail = response.json().get("message", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"GitHub API {response.status_code}: {detail}")
    return response.json()


def build_request_from_github(config: GitHubRequest) -> NarrativeRequest:
    repository = f"{config.owner}/{config.repository}"
    commits_data = _get(
        f"/repos/{repository}/commits",
        config.access_token,
        {"per_page": config.max_items, "since": config.since} if config.since else {"per_page": config.max_items},
    )
    issues_data = _get(
        f"/repos/{repository}/issues",
        config.access_token,
        {"state": "all", "per_page": config.max_items},
    )

    commits: List[CommitInput] = []
    for item in commits_data:
        commit = item.get("commit", {})
        author = (commit.get("author") or {}).get("name") or (item.get("author") or {}).get("login")
        commits.append(
            CommitInput(
                hash=item.get("sha", "")[:12],
                author=author,
                message=(commit.get("message") or "").splitlines()[0],
                files_changed=[],
                diff_summary=commit.get("message"),
            )
        )

    tickets: List[JiraTicketInput] = []
    for item in issues_data:
        if item.get("pull_request"):
            continue
        tickets.append(
            JiraTicketInput(
                key=f"GH-{item.get('number')}",
                summary=item.get("title") or "GitHub issue",
                description=item.get("body") or "No issue description provided.",
            )
        )

    return NarrativeRequest(
        project_name=config.project_name,
        commits=commits,
        jira_tickets=tickets,
    )
