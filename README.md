# ShRED

MVP for an automated SR&ED / Form T661 narrative generator.

## What it does

- Collects commits and issues directly from a GitHub repository.
- Uses a LangChain-based synthesis layer to draft:
  - Scientific Uncertainty
  - Technical Advancement
- Provides a Streamlit UI to connect a repository and review generated narratives.
- Produces a draft on the CRA T661 E (26) template with the project narrative overlaid.

## Project structure

```text
sample_data/
  sample_input.json
src/
  sred_navigator/
    __init__.py
    ai_engine.py
    export.py
    main.py
    models.py
    streamlit_app.py
requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
uvicorn src.sred_navigator.main:app --reload
streamlit run src/sred_navigator/streamlit_app.py
```

## GitHub and T661 workflow

Sign in to the Streamlit MVP with `internal@shred.com` and `password123`.
Add each repository as `owner/repository`. Public repositories work without a
token. For private repositories, create a GitHub fine-grained token with
read-only access to repository metadata, commits, and issues, then paste it
into the project form. The token is sent only to the local API and is not
written to disk.

Evaluate projects individually. Gemini marks each project as Applicable or Not
Applicable based on its evidence. A T661 can be generated only after every
added project has been evaluated; all evaluated projects are included in the
fillable template.

The downloaded PDF preserves the fillable CRA T661 template and populates the
claimant, project, and generated Part 2 narrative fields. The replacement
template is an Adobe XFA document; view the generated file in the latest Adobe
Acrobat Reader rather than a browser PDF viewer. It is a draft for review:
complete all financial, contact, expenditure, certification, and other required
fields in the official CRA workflow before filing.

## Notes

- The synthesis layer requires `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) and uses Gemini Flash.
- If Gemini is not configured, or its response is invalid, the API returns an error; it never substitutes generated text.

```
