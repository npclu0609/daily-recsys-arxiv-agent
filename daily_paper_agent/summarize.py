from __future__ import annotations

import json

import requests

from .models import Paper


SYSTEM_PROMPT = """You are a senior recommender-system researcher. Return strict JSON with keys affiliations, affiliations_zh, subtopics_zh, model_name, summary_zh, practical_value_zh, quality_signal_zh. affiliations and affiliations_zh must be parallel JSON string arrays extracted only from the supplied first-page text; translate institution names into standard Chinese names while keeping brands without an established translation unchanged. subtopics_zh must contain 1-4 concise technical tags such as 生成式推荐, 因果召回, 长序列, 广告精排, 语义 ID. model_name is the explicit method/model acronym from the paper, or an empty string when none exists. Write concise Chinese. Distinguish confirmed venue acceptance from an arXiv preprint. Do not invent affiliations, venues, results, model names, or code availability."""


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
        "topic_zh": paper.topic_zh,
        "detected_model_name": paper.model_name,
        "verified_venue": paper.venue_name,
        "verified_venue_status_zh": paper.venue_status_zh,
        "verified_ccf_rank": paper.ccf_rank,
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
    translated_affiliations = result.get("affiliations_zh", [])
    if isinstance(translated_affiliations, list):
        paper.affiliations_zh = [str(item).strip() for item in translated_affiliations if str(item).strip()][:6]
    subtopics = result.get("subtopics_zh", [])
    if isinstance(subtopics, list):
        paper.subtopics_zh = [str(item).strip() for item in subtopics if str(item).strip()][:4]
    paper.model_name = str(result.get("model_name", "")).strip() or paper.model_name
    paper.summary_zh = result["summary_zh"].strip()
    paper.practical_value_zh = result["practical_value_zh"].strip()
    paper.quality_signal_zh = result["quality_signal_zh"].strip()
