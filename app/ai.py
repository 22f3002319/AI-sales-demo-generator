from __future__ import annotations

import json
import os
from typing import Any, Dict

from openai import OpenAI
import google.generativeai as genai


def _build_prompt(
    *,
    company_name: str,
    website_url: str,
    linkedin_url: str | None,
    founder_background: str | None,
    website_text: str,
    linkedin_text: str,
) -> str:
    return f"""
You are an expert B2B SaaS sales engineer.

Generate a 10-slide sales demo for: {company_name}

INPUTS
- Website URL: {website_url}
- LinkedIn URL: {linkedin_url or "N/A"}
- Founder background: {founder_background or "N/A"}

WEBSITE TEXT (raw)
{website_text[:12000]}

LINKEDIN TEXT (raw; may be empty)
{linkedin_text[:8000]}

OUTPUT FORMAT (STRICT JSON)
Return EXACTLY this JSON shape:
{{
  "company_name": "{company_name}",
  "slides": [
    {{
      "title": "Slide title",
      "subtitle": "Slide subtitle",
      "bullets": ["bullet 1", "bullet 2", "bullet 3"]
    }}
  ]
}}

RULES
- Must contain exactly 10 slides in the "slides" array.
- Each slide must have 3 to 5 bullets.
- Bullets should be concise, concrete, and sales-demo oriented.
- Do not include markdown. Do not include commentary. JSON only.
""".strip()


def _validate_slides(payload: Dict[str, Any]) -> Dict[str, Any]:
    slides = payload.get("slides")
    if not isinstance(slides, list) or len(slides) != 10:
        raise ValueError("AI output must include exactly 10 slides.")

    for i, s in enumerate(slides):
        if not isinstance(s, dict):
            raise ValueError(f"Slide {i+1} must be an object.")
        if not isinstance(s.get("title"), str) or not s["title"].strip():
            raise ValueError(f"Slide {i+1} must have a title.")
        if not isinstance(s.get("subtitle"), str):
            raise ValueError(f"Slide {i+1} must have a subtitle.")
        bullets = s.get("bullets")
        if not isinstance(bullets, list) or not (3 <= len(bullets) <= 5):
            raise ValueError(f"Slide {i+1} must have 3-5 bullets.")
        if not all(isinstance(b, str) and b.strip() for b in bullets):
            raise ValueError(f"Slide {i+1} bullets must be non-empty strings.")

    return payload


def generate_slides_json(
    *,
    company_name: str,
    website_url: str,
    linkedin_url: str | None,
    founder_background: str | None,
    website_text: str,
    linkedin_text: str,
    provider: str = "openai",
    api_key: str | None = None,
) -> Dict[str, Any]:
    prompt = _build_prompt(
        company_name=company_name,
        website_url=website_url,
        linkedin_url=linkedin_url,
        founder_background=founder_background,
        website_text=website_text,
        linkedin_text=linkedin_text,
    )

    provider = (provider or "openai").lower()

    if provider == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("No Gemini API key provided.")
        genai.configure(api_key=key)
        # Use a stable alias that maps to a current Gemini Flash model.
        model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
        model = genai.GenerativeModel(
            model_name,
            generation_config={"response_mime_type": "application/json"},
        )
        resp = model.generate_content(
            [
                "You output only valid JSON.",
                prompt,
            ]
        )
        content = resp.text or "{}"
    else:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("No OpenAI API key provided.")
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "You output only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        content = resp.choices[0].message.content or "{}"

    payload = json.loads(content)
    payload.setdefault("company_name", company_name)
    return _validate_slides(payload)

