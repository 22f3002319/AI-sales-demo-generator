from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


def _normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    text = soup.get_text(" ")
    return _normalize_text(text)


async def fetch_url_text(url: str, *, timeout_ms: int = 45000) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            # Some sites lazy-load; give them a moment but keep it minimal.
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass

            html = await page.content()
            return _html_to_text(html)
        finally:
            await browser.close()


async def scrape_company_content(
    *,
    website_url: str,
    linkedin_url: Optional[str] = None,
) -> dict:
    website_text = await fetch_url_text(website_url)

    linkedin_text = ""
    if linkedin_url:
        try:
            linkedin_text = await fetch_url_text(linkedin_url, timeout_ms=60000)
        except Exception:
            linkedin_text = ""

    return {
        "website_text": website_text,
        "linkedin_text": linkedin_text,
    }

