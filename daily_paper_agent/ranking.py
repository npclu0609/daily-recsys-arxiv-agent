from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import Paper


def _contains(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def match_topic(paper: Paper, topics: dict[str, list[str]]) -> tuple[str, int, int]:
    title = paper.title.lower()
    body = f"{paper.title} {paper.abstract}".lower()
    best_topic = ""
    best_title_hits = 0
    best_body_hits = 0
    best_rank = (0, 0, 0)
    for topic, keywords in topics.items():
        matched_title = [keyword for keyword in keywords if keyword.lower() in title]
        matched_body = [keyword for keyword in keywords if keyword.lower() in body]
        title_hits = len(matched_title)
        body_hits = len(matched_body)
        specificity = sum(len(keyword.split()) for keyword in matched_body)
        rank = (title_hits * 10 + body_hits * 2 + specificity, title_hits, body_hits)
        if rank > best_rank:
            best_topic = topic
            best_title_hits = title_hits
            best_body_hits = body_hits
            best_rank = rank
    return best_topic, best_title_hits, best_body_hits


def preliminary_score(paper: Paper, config: dict, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    topic, title_hits, body_hits = match_topic(paper, config["research"]["topics"])
    paper.topic = topic
    if not topic:
        return 0.0

    combined = f"{paper.title} {paper.abstract} {paper.comment}".lower()
    if any(_contains(combined, keyword) for keyword in config["research"].get("exclude_keywords", [])):
        return 0.0

    score = min(30, title_hits * 10 + body_hits * 3)
    score += min(20, sum(8 for venue in config["quality"]["preferred_venues"] if venue.lower() in paper.comment.lower()))
    score += min(15, sum(5 for term in config["quality"]["evidence_keywords"] if term.lower() in combined))

    published = datetime.fromisoformat(paper.published_at.replace("Z", "+00:00"))
    age_days = max(0, (now - published).days)
    score += max(0, 15 - age_days * 0.5)
    return float(min(80, score))


def enrich_quality_score(paper: Paper, first_pages: str, config: dict) -> float:
    institution_hits = [
        institution
        for institution in config["quality"]["preferred_institutions"]
        if institution.lower() in first_pages.lower()
    ]
    paper.affiliations = list(dict.fromkeys(institution_hits))[:4]
    institution_score = min(15, len(institution_hits) * 5)
    detail_score = 5 if len(first_pages) > 1000 else 0
    paper.quality_score = min(100, paper.quality_score + institution_score + detail_score)
    return paper.quality_score


def select_papers(papers: list[Paper], config: dict) -> list[Paper]:
    limit = config["schedule"]["max_papers_per_day"]
    minimum = config["quality"]["minimum_score"]
    ranked = sorted((paper for paper in papers if paper.quality_score >= minimum), key=lambda p: p.quality_score, reverse=True)

    selected: list[Paper] = []
    topic_counts: dict[str, int] = {}
    for paper in ranked:
        if topic_counts.get(paper.topic, 0) >= max(4, limit // 3):
            continue
        selected.append(paper)
        topic_counts[paper.topic] = topic_counts.get(paper.topic, 0) + 1
        if len(selected) == limit:
            break

    return sorted(selected, key=lambda p: (p.published_at, p.updated_at, p.arxiv_id), reverse=True)
