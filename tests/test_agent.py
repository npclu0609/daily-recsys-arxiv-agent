from datetime import datetime, timezone

from daily_paper_agent.feishu import build_post
from daily_paper_agent.models import Paper
from daily_paper_agent.metadata import detect_venue, enrich_paper_metadata, enrich_record, translate_affiliations
from daily_paper_agent.ranking import match_topic, select_papers
from daily_paper_agent.state import filter_unseen, load_sent, mark_sent
from viewer.build_data import build_data


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


def test_sent_state_keeps_full_paper_record(tmp_path):
    path = tmp_path / "sent.json"
    item = paper("2607.001", "2026-07-25T10:20:00Z", 88, "LLM4Rec")
    mark_sent(path, {"papers": {}}, [item])
    record = load_sent(path)["papers"][item.arxiv_id]
    assert record["summary_zh"] == item.summary_zh
    assert record["published_at"] == item.published_at
    assert record["quality_score"] == 88
    assert record["sent_at"]


def test_viewer_data_is_unique_and_newest_first(tmp_path):
    source = tmp_path / "sent.json"
    target = tmp_path / "papers.json"
    source.write_text(
        '{"papers":{"old":{"title":"Old","published_at":"2026-07-20T00:00:00Z"},'
        '"new":{"title":"New","published_at":"2026-07-25T00:00:00Z"}}}',
        encoding="utf-8",
    )
    payload = build_data(source, target)
    assert payload["count"] == 2
    assert [item["arxiv_id"] for item in payload["papers"]] == ["new", "old"]


def test_ccf_rank_requires_confirmed_acceptance():
    assert detect_venue("Accepted to RecSys 2026") == ("RecSys", "已录用", "B")
    assert detect_venue("Accepted by ACM MM 2026") == ("ACM MM", "已录用", "A")
    assert detect_venue("Submitted to KDD 2026") == ("arXiv", "预印本", "")
    assert detect_venue("Accepted to ICTIR 2026") == ("ICTIR", "已录用", "N")


def test_metadata_is_chinese_and_extracts_model_and_subtopics():
    item = paper("1", "2026-07-25T00:00:00Z", 80, "generative_recommendation")
    item.title = "TSGR: Taobao Search Generative Retrieval"
    item.abstract = "A generative retrieval model using Semantic IDs and a codebook."
    item.affiliations = ["Alibaba", "Zhejiang University"]
    enrich_paper_metadata(item)
    assert item.topic_zh == "生成式推荐"
    assert item.model_name == "TSGR"
    assert "生成式检索" in item.subtopics_zh
    assert item.affiliations_zh == ["阿里巴巴", "浙江大学"]


def test_affiliation_translation_deduplicates():
    assert translate_affiliations(["Tencent", "Tencent Inc."]) == ["腾讯"]


def test_feishu_content_contains_chinese_metadata():
    item = paper("1", "2026-07-25T10:20:00Z", 88, "generative_recommendation")
    item.title = "TopoTok: Topology-Aware Tokenization"
    item.abstract = "Generative recommendation with item tokenization."
    item.comment = "Accepted to RecSys 2026"
    item.affiliations = ["University of Illinois Urbana-Champaign"]
    enrich_paper_metadata(item)
    payload = build_post([item], 1, 1)
    rows = payload["content"]["post"]["zh_cn"]["content"]
    all_text = " ".join(node.get("text", "") for row in rows for node in row)
    assert "RecSys（CCF B，已录用）" in all_text
    assert "伊利诺伊大学厄巴纳-香槟分校" in all_text
    assert "模型/方法：TopoTok" in all_text


def test_archive_removes_unconfirmed_acceptance_claim():
    item = paper("1", "2026-07-25T10:20:00Z", 88).to_dict()
    item["quality_signal_zh"] = "论文已被 RecSys 接收"
    enriched = enrich_record(item)
    assert enriched["venue_status_zh"] == "预印本"
    assert "接收" not in enriched["quality_signal_zh"]
