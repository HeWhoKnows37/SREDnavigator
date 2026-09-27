# SR&ED Navigator

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

Enter a repository as `owner/repository` in the Streamlit app. Public repositories
work without a token. For private repositories, create a GitHub fine-grained
token with read-only access to repository metadata, commits, and issues, then
paste it into the password field. The token is sent only to the local API and
is not written to disk.

The downloaded PDF preserves the fillable CRA T661 template and populates the
claimant, project, and generated Part 2 narrative fields. The replacement
template is an Adobe XFA document; view the generated file in the latest Adobe
Acrobat Reader rather than a browser PDF viewer. It is a draft for review:
complete all financial, contact, expenditure, certification, and other required
fields in the official CRA workflow before filing.

## Notes

- The synthesis layer requires `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) and uses Gemini Flash.
- If Gemini is not configured, or its response is invalid, the API returns an error; it never substitutes generated text.

## API key configuration

Copy `.env.example` to `.env` in the repository root and replace the placeholder
with your Gemini API key:

```dotenv
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.1-flash-lite
```

The application loads `.env` automatically. You can also set `GEMINI_API_KEY`
as an operating-system environment variable. Never commit `.env` or put the key
directly in Python source code.

The Gemini API may restrict which models are available to new accounts. If your
account reports that a model is unavailable, set `GEMINI_MODEL` to the model
name recommended in the API error.
