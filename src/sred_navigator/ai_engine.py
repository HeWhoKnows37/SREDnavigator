from __future__ import annotations

import os
import json
import re
from dataclasses import dataclass
from typing import Dict, List

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from .models import NarrativeRequest, NarrativeResponse

load_dotenv()


@dataclass(frozen=True)
class EvidenceBundle:
    project_name: str
    commit_lines: List[str]
    ticket_lines: List[str]

    @property
    def evidence_lines(self) -> List[str]:
        return self.commit_lines + self.ticket_lines


def _format_commit_lines(request: NarrativeRequest) -> List[str]:
    lines: List[str] = []
    for commit in request.commits:
        changed = ", ".join(commit.files_changed) if commit.files_changed else "No files listed"
        detail = commit.diff_summary or "No diff summary provided"
        lines.append(
            f"- Commit {commit.hash} by {commit.author or 'unknown author'}: "
            f"{commit.message}. Files: {changed}. Change summary: {detail}."
        )
    return lines


def _format_ticket_lines(request: NarrativeRequest) -> List[str]:
    lines: List[str] = []
    for ticket in request.jira_tickets:
        description = ticket.description or "No description provided"
        lines.append(f"- Ticket {ticket.key}: {ticket.summary}. Description: {description}.")
    return lines


def build_evidence_bundle(request: NarrativeRequest) -> EvidenceBundle:
    return EvidenceBundle(
        project_name=request.project_name,
        commit_lines=_format_commit_lines(request),
        ticket_lines=_format_ticket_lines(request),
    )


def _parse_generated_text(text: str) -> Dict[str, str]:
    sections = {
        "scientific_uncertainty": "",
        "technical_advancement": "",
        "evidence_summary": "",
    }
    try:
        parsed_json = json.loads(text)
    except json.JSONDecodeError:
        parsed_json = None
    if isinstance(parsed_json, dict):
        sections = {
            "scientific_uncertainty": str(parsed_json.get("scientific_uncertainty", "")).strip(),
            "technical_advancement": str(parsed_json.get("technical_advancement", "")).strip(),
            "evidence_summary": str(parsed_json.get("evidence_summary", "")).strip(),
        }
        missing = [name for name, value in sections.items() if not value]
        if not missing:
            return sections

    current_key = None
    buffer: List[str] = []
    heading_patterns = [
        (re.compile(r"^(?:[#>*\-\s\d.)]+)?evidence\s+summary\s*:?\s*(.*)$", re.IGNORECASE), "evidence_summary"),
        (re.compile(r"^(?:[#>*\-\s\d.)]+)?scientific(?:\s+and\s+technological|/technological)?\s+uncertainty\s*:?\s*(.*)$", re.IGNORECASE), "scientific_uncertainty"),
        (re.compile(r"^(?:[#>*\-\s\d.)]+)?technical\s+advancement\s*:?\s*(.*)$", re.IGNORECASE), "technical_advancement"),
    ]

    def flush() -> None:
        nonlocal buffer, current_key
        if current_key:
            sections[current_key] = " ".join(part.strip() for part in buffer if part.strip()).strip()
        buffer = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        clean_line = line.strip("*_#>- ")
        for pattern, key in heading_patterns:
            match = pattern.match(clean_line)
            if match:
                flush()
                current_key = key
                content = match.group(1).strip(" *_#>-")
                if content:
                    buffer.append(content)
                break
        else:
            if current_key:
                buffer.append(clean_line)
    flush()

    missing = [name for name, value in sections.items() if not value]
    if missing:
        raise ValueError(f"Gemini response omitted required sections: {', '.join(missing)}")
    return sections


def _build_chain():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    from langchain_google_genai import ChatGoogleGenerativeAI

    template = PromptTemplate.from_template(
        """
You are drafting CRA-style SR&ED Form T661 narratives from technical evidence.

Rules:
- Use only the supplied evidence.
- Write in plain, audit-friendly language.
- Produce exactly these sections, using these exact headings:
  Evidence summary:
  Scientific Uncertainty:
  Technical Advancement:
- Return plain text with one heading per line. Do not use Markdown, JSON, or tables.
- If evidence is thin, state that clearly instead of inventing facts.

Project: {project_name}

Evidence:
{evidence}
""".strip()
    )
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        google_api_key=api_key,
        temperature=0,
    )
    return template | llm | StrOutputParser()


def generate_narrative(request: NarrativeRequest, source_repository: str | None = None) -> NarrativeResponse:
    bundle = build_evidence_bundle(request)
    raw_output = _build_chain().invoke(
        {
            "project_name": bundle.project_name,
            "evidence": "\n".join(bundle.evidence_lines) if bundle.evidence_lines else "- No evidence supplied",
        }
    )
    parsed = _parse_generated_text(raw_output)
    return NarrativeResponse(
        project_name=bundle.project_name,
        scientific_uncertainty=parsed["scientific_uncertainty"],
        technical_advancement=parsed["technical_advancement"],
        evidence_summary=parsed["evidence_summary"],
        source_commit_count=len(request.commits),
        source_ticket_count=len(request.jira_tickets),
        used_llm=True,
        source_repository=source_repository,
    )
