from __future__ import annotations

import io
import html
import math
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests
from pypdf import PdfReader

from .models import Paper


ARXIV_API = "https://export.arxiv.org/api/query"
ATOM = {"a": "http://www.w3.org/2005/Atom"}


def _text(node: ET.Element | None) -> str:
    return re.sub(r"\s+", " ", node.text or "").strip() if node is not None else ""


def fetch_papers(categories: list[str], limit: int, timeout: int = 45) -> list[Paper]:
    per_category = max(1, math.ceil(limit / len(categories)))
    papers_by_id: dict[str, Paper] = {}
    for category_index, category in enumerate(categories):
        response = requests.get(
            ARXIV_API,
            params={
                "search_query": f"cat:{category}",
                "start": 0,
                "max_results": per_category,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            },
            headers={"User-Agent": "daily-recsys-arxiv-agent/0.1"},
            timeout=timeout,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
        for entry in root.findall("a:entry", ATOM):
            raw_id = _text(entry.find("a:id", ATOM)).rsplit("/", 1)[-1]
            arxiv_id = raw_id.split("v", 1)[0]
            authors = [_text(author.find("a:name", ATOM)) for author in entry.findall("a:author", ATOM)]
            categories_found = [node.attrib.get("term", "") for node in entry.findall("a:category", ATOM)]
            comment_node = entry.find("{http://arxiv.org/schemas/atom}comment")
            papers_by_id[arxiv_id] = Paper(
                arxiv_id=arxiv_id,
                title=_text(entry.find("a:title", ATOM)),
                abstract=_text(entry.find("a:summary", ATOM)),
                authors=authors,
                categories=categories_found,
                published_at=_text(entry.find("a:published", ATOM)),
                updated_at=_text(entry.find("a:updated", ATOM)),
                abs_url=f"https://arxiv.org/abs/{arxiv_id}",
                pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
                comment=_text(comment_node),
            )
        if category_index < len(categories) - 1:
            time.sleep(1)
    return sorted(papers_by_id.values(), key=lambda paper: paper.published_at, reverse=True)[:limit]


def in_lookback(paper: Paper, days: int, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    published = datetime.fromisoformat(paper.published_at.replace("Z", "+00:00"))
    return published >= now - timedelta(days=days)


def extract_first_pages_text(paper: Paper, timeout: int = 30, pdf_fallback: bool = False) -> str:
    html_response = requests.get(
        f"https://arxiv.org/html/{paper.arxiv_id}",
        headers={"User-Agent": "daily-recsys-arxiv-agent/0.1"},
        timeout=min(timeout, 15),
    )
    if html_response.ok and "<html" in html_response.text[:1000].lower():
        cleaned = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html_response.text)
        cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", html.unescape(cleaned)).strip()
        if len(cleaned) >= 500:
            return cleaned[:16000]

    if not pdf_fallback:
        return ""

    response = requests.get(
        paper.pdf_url,
        headers={"User-Agent": "daily-recsys-arxiv-agent/0.1"},
        timeout=timeout,
    )
    response.raise_for_status()
    reader = PdfReader(io.BytesIO(response.content))
    text = "\n".join((page.extract_text() or "") for page in reader.pages[:2])
    return text[:16000]
