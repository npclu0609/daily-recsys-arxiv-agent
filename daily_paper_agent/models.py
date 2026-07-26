from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Paper:
    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    published_at: str
    updated_at: str
    abs_url: str
    pdf_url: str
    comment: str = ""
    affiliations: list[str] = field(default_factory=list)
    affiliations_zh: list[str] = field(default_factory=list)
    topic: str = ""
    topic_zh: str = ""
    subtopics_zh: list[str] = field(default_factory=list)
    model_name: str = ""
    venue_name: str = ""
    venue_status_zh: str = ""
    ccf_rank: str = ""
    quality_score: float = 0.0
    summary_zh: str = ""
    practical_value_zh: str = ""
    quality_signal_zh: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
