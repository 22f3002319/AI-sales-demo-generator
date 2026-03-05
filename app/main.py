from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .ai import generate_slides_json
from .database import SessionLocal, init_db
from .models import Demo
from .scraper import scrape_company_content


app = FastAPI(title="AI Sales Demo Generator")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def index(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "error": error},
    )


async def _parse_generate_payload(request: Request) -> Dict[str, Any]:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        data = await request.json()
        return dict(data)
    form = await request.form()
    return dict(form)


@app.post("/generate-demo")
async def generate_demo(request: Request):
    data = await _parse_generate_payload(request)

    company_name = (data.get("company_name") or "").strip()
    website_url = (data.get("website_url") or "").strip()
    linkedin_url = (data.get("linkedin_url") or "").strip() or None
    founder_background = (data.get("founder_background") or "").strip() or None
    provider = (data.get("provider") or "openai").strip().lower()
    api_key = (data.get("api_key") or "").strip() or None

    if not company_name or not website_url:
        if "text/html" in (request.headers.get("accept") or ""):
            return index(request, error="Company name and website URL are required.")
        raise HTTPException(status_code=400, detail="company_name and website_url are required")

    is_html_flow = ("text/html" in (request.headers.get("accept") or "")) or (
        "application/x-www-form-urlencoded" in (request.headers.get("content-type") or "")
    )

    try:
        scraped = await scrape_company_content(website_url=website_url, linkedin_url=linkedin_url)
        slides_payload = generate_slides_json(
            company_name=company_name,
            website_url=website_url,
            linkedin_url=linkedin_url,
            founder_background=founder_background,
            website_text=scraped["website_text"],
            linkedin_text=scraped["linkedin_text"],
            provider=provider,
            api_key=api_key,
        )
    except Exception as e:
        if is_html_flow:
            return index(request, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    # Persist
    with SessionLocal() as db:
        demo = Demo(company_name=company_name, slides_json=json.dumps(slides_payload["slides"]))
        db.add(demo)
        db.commit()
        db.refresh(demo)

    # HTML form flow redirects to shareable link
    if is_html_flow:
        return RedirectResponse(url=f"/demo/{demo.id}", status_code=303)

    return {"id": demo.id, "company_name": demo.company_name, "created_at": demo.created_at.isoformat()}


@app.get("/demo/{id}", response_class=HTMLResponse)
def get_demo(id: int, request: Request):
    with SessionLocal() as db:
        demo = db.get(Demo, id)
        if not demo:
            raise HTTPException(status_code=404, detail="Demo not found")
        slides = json.loads(demo.slides_json)

    return templates.TemplateResponse(
        "slides.html",
        {
            "request": request,
            "demo": demo,
            "slides_json": json.dumps(slides),
        },
    )


@app.get("/health")
def health():
    return {"ok": True, "ts": datetime.utcnow().isoformat() + "Z"}

