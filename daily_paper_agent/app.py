from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .arxiv import extract_first_pages_text, fetch_papers, in_lookback
from .config import load_config
from .feishu import send_papers
from .ranking import enrich_quality_score, preliminary_score, select_papers
from .state import filter_unseen, load_sent, mark_sent
from .summarize import summarize_paper


def run(
    config_path: str,
    dry_run: bool = False,
    max_papers: int | None = None,
    candidate_limit: int | None = None,
    pdf_limit: int | None = None,
) -> list:
    config = load_config(config_path)
    if max_papers is not None:
        config["schedule"]["max_papers_per_day"] = max_papers
    if candidate_limit is not None:
        config["schedule"]["candidate_limit"] = candidate_limit
    if pdf_limit is not None:
        config["schedule"]["pdf_enrichment_limit"] = pdf_limit
    root = Path(config["_root"])
    sent_path = root / config["state"]["sent_file"]
    latest_path = root / config["state"]["latest_file"]
    state = load_sent(sent_path)

    fetched = fetch_papers(
        config["research"]["arxiv_categories"],
        config["schedule"]["candidate_limit"],
    )
    candidates = [
        paper
        for paper in filter_unseen(fetched, state)
        if in_lookback(paper, config["schedule"]["lookback_days"])
    ]
    for paper in candidates:
        paper.quality_score = preliminary_score(paper, config)

    candidates = sorted(candidates, key=lambda p: p.quality_score, reverse=True)[
        : config["schedule"]["pdf_enrichment_limit"]
    ]
    page_text: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=config["schedule"]["pdf_workers"]) as executor:
        futures = {
            executor.submit(
                extract_first_pages_text,
                paper,
                30,
                config["schedule"].get("pdf_fallback_enabled", False),
            ): paper
            for paper in candidates
        }
        for future in as_completed(futures):
            paper = futures[future]
            try:
                page_text[paper.arxiv_id] = future.result()
            except Exception as exc:
                print(f"[WARN] PDF extraction failed for {paper.arxiv_id}: {exc}")
                page_text[paper.arxiv_id] = ""
    for paper in candidates:
        enrich_quality_score(paper, page_text[paper.arxiv_id], config)

    selected = select_papers(candidates, config)
    for paper in selected:
        summarize_paper(paper, config, page_text[paper.arxiv_id])

    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(
        json.dumps({"count": len(selected), "papers": [paper.to_dict() for paper in selected]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not selected:
        print("[INFO] No unseen papers passed the quality threshold")
        return []
    if dry_run:
        print(f"[DRY RUN] Selected {len(selected)} papers; no Feishu message sent")
        return selected

    send_papers(selected, config)
    mark_sent(sent_path, state, selected)
    print(f"[OK] Sent and recorded {len(selected)} papers")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily configurable arXiv digest for Feishu")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-papers", type=int, help="Override max papers for this run")
    parser.add_argument("--candidate-limit", type=int, help="Override arXiv candidate count")
    parser.add_argument("--pdf-limit", type=int, help="Override PDF enrichment count")
    args = parser.parse_args()
    run(args.config, args.dry_run, args.max_papers, args.candidate_limit, args.pdf_limit)
