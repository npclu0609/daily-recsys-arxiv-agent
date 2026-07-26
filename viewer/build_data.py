from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "sent_papers.json"
TARGET = Path(__file__).with_name("papers_data.json")


def build_data(source: Path = SOURCE, target: Path = TARGET) -> dict:
    state = json.loads(source.read_text(encoding="utf-8")) if source.exists() else {"papers": {}}
    papers = []
    for arxiv_id, record in state.get("papers", {}).items():
        item = dict(record)
        item.setdefault("arxiv_id", arxiv_id)
        # Old state entries remain valid for deduplication and degrade gracefully in the viewer.
        item.setdefault("title", arxiv_id)
        papers.append(item)
    papers.sort(key=lambda item: item.get("published_at", ""), reverse=True)
    payload = {"count": len(papers), "papers": papers}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = build_data()
    print(f"Built archive with {result['count']} papers")
