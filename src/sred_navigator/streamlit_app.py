from __future__ import annotations

import requests
import streamlit as st


API_URL = "http://localhost:8000"


st.set_page_config(page_title="SR&ED Navigator", layout="wide")
st.title("SR&ED Navigator")
st.caption("Connect a GitHub repository to collect evidence and prepare a CRA T661 draft.")

with st.form("github_form"):
    col_left, col_right = st.columns(2)
    with col_left:
        repository = st.text_input("GitHub repository", placeholder="owner/repository")
        project_name = st.text_input("Project name", value="SR&ED Navigator")
        claimant_name = st.text_input("Claimant name")
        project_code = st.text_input("Project code")
    with col_right:
        access_token = st.text_input("GitHub token (optional for public repositories)", type="password")
        tax_year_start = st.text_input("Tax year start", placeholder="YYYY-MM-DD")
        tax_year_end = st.text_input("Tax year end", placeholder="YYYY-MM-DD")
        since = st.text_input("Collect commits since (optional)", placeholder="YYYY-MM-DD")
    submitted = st.form_submit_button("Collect evidence and generate T661")

if submitted:
    try:
        owner, repo = repository.strip().split("/", 1)
        payload = {
            "owner": owner,
            "repository": repo,
            "project_name": project_name,
            "access_token": access_token or None,
            "since": since or None,
        }
        with st.spinner("Collecting GitHub evidence and generating narratives..."):
            response = requests.post(f"{API_URL}/api/github/synthesize", json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            st.success("Narratives generated")
            st.subheader("Evidence Summary")
            st.write(data["evidence_summary"])
            st.subheader("Scientific Uncertainty")
            st.write(data["scientific_uncertainty"])
            st.subheader("Technical Advancement")
            st.write(data["technical_advancement"])
            st.caption(f"Repository: {data.get('source_repository')} | Used LLM: {data['used_llm']}")
            export_response = requests.post(
                f"{API_URL}/api/export/t661",
                json={
                    "narrative": data,
                    "claimant_name": claimant_name,
                    "tax_year_start": tax_year_start,
                    "tax_year_end": tax_year_end,
                    "project_title": project_name,
                    "project_code": project_code,
                },
                timeout=60,
            )
            export_response.raise_for_status()
            st.download_button(
                "Download CRA T661 draft",
                data=export_response.content,
                file_name="t661-sred-claim.pdf",
                mime="application/pdf",
            )
    except requests.RequestException as exc:
        detail = ""
        if exc.response is not None:
            try:
                detail = f" — {exc.response.json().get('detail', '')}"
            except ValueError:
                detail = f" — {exc.response.text}"
        st.error(f"API request failed: {exc}{detail}")
    except ValueError:
        st.error("Enter the repository in owner/repository format.")
