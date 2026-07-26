from __future__ import annotations

import json

import requests

from .models import Paper


SYSTEM_PROMPT = """You are a senior recommender-system researcher. Return strict JSON with keys affiliations, summary_zh, practical_value_zh, quality_signal_zh. affiliations must be a JSON string array extracted only from the supplied first-page text. Write concise Chinese. Distinguish confirmed venue acceptance from an arXiv preprint. Do not invent affiliations, venues, results, or code availability."""


def summarize_paper(paper: Paper, config: dict, first_pages: str) -> None:
    llm = config["llm"]
    if not llm.get("enabled") or not llm.get("api_key"):
        paper.summary_zh = paper.abstract
        paper.practical_value_zh = "请结合业务场景进一步评估。"
        paper.quality_signal_zh = f"质量评分 {paper.quality_score:.0f}/100；未启用 LLM 中文总结。"
        return

    user_payload = {
        "title": paper.title,
        "abstract": paper.abstract,
        "authors": paper.authors,
        "arxiv_comment": paper.comment,
        "detected_affiliations": paper.affiliations,
        "first_pages_excerpt": first_pages[:7000],
        "quality_score": paper.quality_score,
    }
    payload = {
        "model": llm["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_object"},
    }
    url = f"{llm['base_url'].rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {llm['api_key']}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=payload, timeout=llm["timeout_seconds"])
    if response.status_code == 400:
        payload.pop("response_format")
        response = requests.post(url, headers=headers, json=payload, timeout=llm["timeout_seconds"])
    if not response.ok:
        detail = response.text[:500].replace("\n", " ")
        raise RuntimeError(f"LLM request failed with HTTP {response.status_code}: {detail}")
    content = response.json()["choices"][0]["message"]["content"]
    result = json.loads(content)
    extracted_affiliations = result.get("affiliations", [])
    if isinstance(extracted_affiliations, list):
        paper.affiliations = list(dict.fromkeys(paper.affiliations + [str(item).strip() for item in extracted_affiliations if str(item).strip()]))[:6]
    paper.summary_zh = result["summary_zh"].strip()
    paper.practical_value_zh = result["practical_value_zh"].strip()
    paper.quality_signal_zh = result["quality_signal_zh"].strip()
