from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CommitInput(BaseModel):
    hash: str = Field(..., description="Git commit hash or identifier")
    author: Optional[str] = Field(default=None, description="Commit author")
    message: str = Field(..., description="Commit message")
    files_changed: List[str] = Field(default_factory=list, description="Files touched by the commit")
    diff_summary: Optional[str] = Field(default=None, description="Short summary of the technical changes")


class JiraTicketInput(BaseModel):
    key: str = Field(..., description="Jira issue key")
    summary: str = Field(..., description="Ticket summary")
    description: Optional[str] = Field(default=None, description="Ticket description")


class NarrativeRequest(BaseModel):
    project_name: str = Field(default="SR&ED Navigator")
    commits: List[CommitInput] = Field(default_factory=list)
    jira_tickets: List[JiraTicketInput] = Field(default_factory=list)


class GitHubRequest(BaseModel):
    owner: str = Field(..., min_length=1)
    repository: str = Field(..., min_length=1)
    project_name: str = Field(default="SR&ED Navigator")
    access_token: Optional[str] = None
    since: Optional[str] = Field(default=None, description="ISO date for earliest evidence")
    max_items: int = Field(default=50, ge=1, le=100)


class NarrativeResponse(BaseModel):
    project_name: str
    scientific_uncertainty: str
    technical_advancement: str
    evidence_summary: str
    source_commit_count: int
    source_ticket_count: int
    used_llm: bool
    source_repository: Optional[str] = None


class T661ExportRequest(BaseModel):
    narrative: NarrativeResponse
    claimant_name: str = ""
    tax_year_start: str = ""
    tax_year_end: str = ""
    project_title: str = ""
    project_code: str = ""
