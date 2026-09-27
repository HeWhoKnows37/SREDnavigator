from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from tempfile import NamedTemporaryFile
from fastapi.middleware.cors import CORSMiddleware

from .ai_engine import generate_narrative
from .export import export_narrative_to_t661
from .github import build_request_from_github
from .models import GitHubRequest, NarrativeRequest, NarrativeResponse, T661ExportRequest

app = FastAPI(title="SR&ED Navigator API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/synthesize", response_model=NarrativeResponse)
def synthesize_narrative(payload: NarrativeRequest) -> NarrativeResponse:
    try:
        return generate_narrative(payload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI provider request failed: {exc}") from exc


@app.post("/api/github/synthesize", response_model=NarrativeResponse)
def synthesize_github_narrative(payload: GitHubRequest) -> NarrativeResponse:
    try:
        request = build_request_from_github(payload)
        return generate_narrative(request, source_repository=f"{payload.owner}/{payload.repository}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GitHub or AI provider request failed: {exc}") from exc


@app.post("/api/export/t661")
def export_t661(payload: T661ExportRequest) -> FileResponse:
    try:
        output = NamedTemporaryFile(suffix=".pdf", delete=False)
        output.close()
        path = export_narrative_to_t661(
            payload.narrative,
            output.name,
            claimant_name=payload.claimant_name,
            tax_year_start=payload.tax_year_start,
            tax_year_end=payload.tax_year_end,
            project_title=payload.project_title or payload.narrative.project_name,
            project_code=payload.project_code,
        )
        return FileResponse(path, media_type="application/pdf", filename="t661-sred-claim.pdf")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"T661 export failed: {exc}") from exc
