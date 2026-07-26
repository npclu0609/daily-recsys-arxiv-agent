from datetime import datetime, timezone

from daily_paper_agent.feishu import build_post
from daily_paper_agent.models import Paper
from daily_paper_agent.ranking import match_topic, select_papers
from daily_paper_agent.state import filter_unseen


def paper(arxiv_id: str, published: str, score: float, topic: str = "recsys") -> Paper:
    return Paper(
        arxiv_id=arxiv_id,
        title=f"Paper {arxiv_id}",
        abstract="recommendation ranking",
        authors=["A. Author"],
        categories=["cs.IR"],
        published_at=published,
        updated_at=published,
        abs_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        topic=topic,
        quality_score=score,
        summary_zh="中文总结",
        practical_value_zh="工程价值",
        quality_signal_zh="质量依据",
    )


def test_filter_unseen():
    papers = [paper("1", "2026-07-25T00:00:00Z", 90), paper("2", "2026-07-24T00:00:00Z", 80)]
    assert [item.arxiv_id for item in filter_unseen(papers, {"papers": {"1": {}}})] == ["2"]


def test_selection_is_sorted_newest_first():
    config = {"schedule": {"max_papers_per_day": 20}, "quality": {"minimum_score": 45}}
    papers = [paper("old", "2026-07-20T00:00:00Z", 99), paper("new", "2026-07-25T00:00:00Z", 80)]
    assert [item.arxiv_id for item in select_papers(papers, config)] == ["new", "old"]


def test_topic_matching():
    item = paper("1", "2026-07-25T00:00:00Z", 0)
    item.title = "Generative Recommendation with Semantic IDs"
    topic, title_hits, _ = match_topic(item, {"genrec": ["generative recommendation", "semantic id"]})
    assert topic == "genrec"
    assert title_hits == 2


def test_more_specific_topic_wins_tie():
    item = paper("1", "2026-07-25T00:00:00Z", 0)
    item.title = "A Filter for Industrial Ad Recommendation"
    topic, _, _ = match_topic(
        item,
        {
            "general": ["recommendation"],
            "ads": ["ad recommendation"],
        },
    )
    assert topic == "ads"


def test_feishu_content_contains_publish_time():
    payload = build_post([paper("1", "2026-07-25T10:20:00Z", 88)], 1, 1)
    rows = payload["content"]["post"]["zh_cn"]["content"]
    all_text = " ".join(node.get("text", "") for row in rows for node in row)
    assert "首次上传：2026-07-25 10:20 UTC" in all_text
