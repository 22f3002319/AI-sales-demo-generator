# AI Sales Demo Generator (Minimal MVP)

Generate a **10-slide sales demo** from a company website URL (and optional LinkedIn URL), store it in **SQLite**, and render a **shareable** slide deck at `/demo/{id}`.

## Requirements

- Python 3.10+ (3.11 recommended)
- For OpenAI: `OPENAI_API_KEY`
- For Gemini: `GEMINI_API_KEY`

## Run locally (Windows / PowerShell)

```powershell
cd "c:\Users\Mehak\AI sales demo generator"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/`.

## API

- `POST /generate-demo`
  - Accepts **HTML form** or **JSON**
  - Fields:
    - `company_name` (required)
    - `website_url` (required)
    - `linkedin_url` (optional)
    - `founder_background` (optional)
  - Returns:
    - HTML flow: redirects to `/demo/{id}`
    - JSON flow: `{ id, company_name, created_at }`

- `GET /demo/{id}`
  - Renders the slide deck (Tailwind + next/prev + shareable link)

## Environment variables

- `OPENAI_API_KEY` (for OpenAI provider)
- `OPENAI_MODEL` (optional, default: `gpt-4o-mini`)
- `GEMINI_API_KEY` (for Gemini provider)
- `GEMINI_MODEL` (optional, default: `gemini-flash-latest`)
- `DATABASE_URL` (optional, default: `sqlite:///./demos.db`)
- `PORT` (optional, default 8000; Docker uses 8000)

## Docker

```bash
docker build -t ai-sales-demo .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY="YOUR_OPENAI_KEY" \
  -e GEMINI_API_KEY="YOUR_GEMINI_KEY" \
  ai-sales-demo
```

Open `http://127.0.0.1:8000/`.

## Deployment notes (Railway / Render / Fly.io)

- **Set env vars**: `OPENAI_API_KEY` and/or `GEMINI_API_KEY`
- **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **SQLite warning**: SQLite is fine for an MVP, but on some platforms the filesystem may be ephemeral. If that’s a concern, switch `DATABASE_URL` to Postgres later.

