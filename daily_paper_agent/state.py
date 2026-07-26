from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .models import Paper


def load_sent(path: Path) -> dict:
    if not path.exists():
        return {"papers": {}}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data.get("papers"), dict):
        raise ValueError("State file must contain a papers object")
    return data


def filter_unseen(papers: list[Paper], state: dict) -> list[Paper]:
    return [paper for paper in papers if paper.arxiv_id not in state["papers"]]


def mark_sent(path: Path, state: dict, papers: list[Paper]) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    for paper in papers:
        state["papers"][paper.arxiv_id] = {"title": paper.title, "sent_at": timestamp}
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="sent-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

