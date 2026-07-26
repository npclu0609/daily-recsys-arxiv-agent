from __future__ import annotations

from datetime import datetime

import requests

from .models import Paper


def _date(value: str) -> str:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M UTC")


def _venue_label(paper: Paper) -> str:
    if paper.ccf_rank in {"A", "B", "C"}:
        return f"{paper.venue_name}（CCF {paper.ccf_rank}，{paper.venue_status_zh}）"
    if paper.ccf_rank == "N":
        return f"{paper.venue_name}（非 CCF 推荐目录，{paper.venue_status_zh}）"
    return "arXiv 预印本"


def build_post(papers: list[Paper], part: int, total_parts: int) -> dict:
    rows: list[list[dict]] = []
    for index, paper in enumerate(papers, 1):
        affiliations = " × ".join(paper.affiliations_zh or paper.affiliations) or "未可靠提取"
        tags = " ".join(f"【{tag}】" for tag in paper.subtopics_zh)
        rows.extend(
            [
                [{"tag": "a", "text": f"{index}. {paper.title}", "href": paper.abs_url}],
                [{"tag": "text", "text": f"{_venue_label(paper)}｜{affiliations}｜{tags}"}],
                [{"tag": "text", "text": f"首次上传：{_date(paper.published_at)}｜最近更新：{_date(paper.updated_at)}"}],
            ]
        )
        if paper.model_name:
            rows.append([{"tag": "text", "text": f"模型/方法：{paper.model_name}"}])
        rows.extend(
            [
                [{"tag": "text", "text": f"作者：{', '.join(paper.authors[:8])}"}],
                [{"tag": "text", "text": f"中文总结：{paper.summary_zh}"}],
                [{"tag": "text", "text": f"为什么值得读：{paper.practical_value_zh}"}],
                [{"tag": "text", "text": f"入选依据：{paper.quality_signal_zh}｜质量分 {paper.quality_score:.0f}/100"}],
                [{"tag": "text", "text": " "}],
            ]
        )
    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"每日优质论文（{part}/{total_parts}）",
                    "content": rows,
                }
            }
        },
    }


def send_papers(papers: list[Paper], config: dict) -> None:
    webhook = config["feishu"].get("webhook_url")
    if not webhook:
        raise RuntimeError(f"Missing environment variable: {config['feishu']['webhook_env']}")
    chunk_size = config["schedule"]["message_chunk_size"]
    chunks = [papers[index : index + chunk_size] for index in range(0, len(papers), chunk_size)]
    for index, chunk in enumerate(chunks, 1):
        response = requests.post(
            webhook,
            json=build_post(chunk, index, len(chunks)),
            timeout=config["feishu"]["timeout_seconds"],
        )
        response.raise_for_status()
        result = response.json()
        if result.get("code", result.get("StatusCode", 0)) != 0:
            raise RuntimeError(f"Feishu rejected message: {result}")
