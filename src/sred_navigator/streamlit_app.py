from __future__ import annotations

import requests
import streamlit as st


API_URL = "http://localhost:8000"
VALID_EMAIL = "internal@shred.com"
VALID_PASSWORD = "password123"


def api_error(exc: requests.RequestException) -> str:
    if exc.response is not None:
        try:
            return str(exc.response.json().get("detail", exc.response.text))
        except ValueError:
            return exc.response.text
    return str(exc)


st.set_page_config(page_title="ShRED", page_icon="💧", layout="wide")
st.markdown(
    """
    <style>
    :root {
        --shred-blue: #b9dff2;
        --shred-blue-dark: #2f6f91;
        --shred-ink: #173042;
        --shred-surface: #dbe7ed;
    }
    [data-testid="stTextInput"] label,
    [data-testid="stTextInput"] label p,
    [data-testid="stForm"] label,
    [data-testid="stForm"] label p,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary p {
        color: #173042 !important;
    }
    [data-testid="stForm"] h1,
    [data-testid="stForm"] h2,
    [data-testid="stForm"] h3 {
        color: #173042 !important;
    }
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3 {
        color: #173042 !important;
    }
    .stApp {
        background: var(--shred-surface);
        color: var(--shred-ink);
    }
    [data-testid="stHeader"] {
        background: rgba(219, 231, 237, 0.95);
    }
    [data-testid="stSidebar"] {
        background: var(--shred-blue);
    }
    .stButton > button, .stFormSubmitButton > button {
        background: var(--shred-blue);
        border: 1px solid var(--shred-blue-dark);
        color: var(--shred-ink);
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        background: #9ecfe8;
        border-color: var(--shred-blue-dark);
        color: var(--shred-ink);
    }
    [data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--shred-blue);
        background: #ffffff;
    }
    [data-testid="stTextInput"] input {
        background: #eef1f3;
        border-color: #c3cdd2;
        color: var(--shred-ink);
        -webkit-text-fill-color: var(--shred-ink);
        caret-color: var(--shred-ink);
    }
    [data-testid="stTextInput"] input::placeholder {
        color: #657783;
        opacity: 1;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: var(--shred-blue-dark);
        box-shadow: 0 0 0 1px var(--shred-blue-dark);
    }
    .st-key-login-column {
        min-height: 66vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    div[data-testid="stForm"] {
        border: 0;
    }
    .st-key-login-column div[data-testid="stForm"] {
        min-height: 66vh;
        padding: 3rem 2.5rem;
        background: #f7fbfd;
        border: 1px solid #c3d6df;
        border-radius: 12px;
        box-shadow: 0 14px 35px rgba(23, 48, 66, 0.22);
        box-sizing: border-box;
    }
    @media (max-width: 700px) {
        .st-key-login-column div[data-testid="stForm"] {
            min-height: 66vh;
            padding: 2rem 1.25rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "projects" not in st.session_state:
    st.session_state.projects = []

if not st.session_state.authenticated:
    _, login_column, _ = st.columns([1, 1, 1])
    with login_column:
        with st.container(key="login-column"):
            st.title("ShRED")
            st.caption("Internal MVP dashboard")
            with st.form("login"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign in")
    if submitted:
        if email == VALID_EMAIL and password == VALID_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid email or password.")
    st.stop()

title_column, sign_out_column = st.columns([5, 1])
with title_column:
    st.title("ShRED")
with sign_out_column:
    if st.button("Sign out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

with st.expander("Add project", expanded=not st.session_state.projects):
    with st.form("add_project"):
        repository = st.text_input("GitHub repository", placeholder="owner/repository")
        project_name = st.text_input("Project name")
        access_token = st.text_input("GitHub token (optional for public repositories)", type="password")
        since = st.text_input("Collect commits since (optional)", placeholder="YYYY-MM-DD")
        add = st.form_submit_button("Add project")
    if add:
        try:
            owner, repo = repository.strip().split("/", 1)
            if not project_name.strip():
                raise ValueError("Project name is required.")
            st.session_state.projects.append(
                {
                    "owner": owner,
                    "repository": repo,
                    "project_name": project_name.strip(),
                    "access_token": access_token or None,
                    "since": since or None,
                    "narrative": None,
                }
            )
            st.success("Project added.")
        except ValueError:
            st.error("Enter a project name and repository in owner/repository format.")

st.subheader("Projects")
for index, project in enumerate(st.session_state.projects):
    narrative = project["narrative"]
    label = f"{project['project_name']} ({project['owner']}/{project['repository']})"
    with st.container(border=True):
        st.markdown(f"### {label}")
        if narrative:
            status = "Applicable" if narrative["applicable"] else "Not applicable"
            st.write(f"**SR&ED status:** {status}")
            st.caption(narrative["applicability_reason"])
            st.write(narrative["evidence_summary"])
        else:
            st.info("Not evaluated.")
        if st.button("Evaluate project", key=f"evaluate-{index}"):
            payload = {
                "owner": project["owner"],
                "repository": project["repository"],
                "project_name": project["project_name"],
                "access_token": project["access_token"],
                "since": project["since"],
            }
            try:
                with st.spinner("Collecting evidence and evaluating with Gemini..."):
                    response = requests.post(f"{API_URL}/api/github/synthesize", json=payload, timeout=180)
                    response.raise_for_status()
                    project["narrative"] = response.json()
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Evaluation failed: {api_error(exc)}")

evaluated = [p for p in st.session_state.projects if p["narrative"]]
if evaluated and len(evaluated) == len(st.session_state.projects):
    st.divider()
    st.subheader("Generate T661")
    st.caption("Filer: JJ Jameson | Tax year: January 1, 2026 to December 31, 2026")
    if st.button("Generate T661 for evaluated projects"):
        try:
            response = requests.post(
                f"{API_URL}/api/export/t661",
                json={
                    "narratives": [p["narrative"] for p in evaluated],
                },
                timeout=120,
            )
            response.raise_for_status()
            st.download_button(
                "Download T661",
                data=response.content,
                file_name="t661-sred-claim.pdf",
                mime="application/pdf",
            )
        except requests.RequestException as exc:
            st.error(f"T661 generation failed: {api_error(exc)}")
elif st.session_state.projects:
    st.info("Evaluate every project before generating the T661.")
