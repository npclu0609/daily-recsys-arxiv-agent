from __future__ import annotations

import re

from .models import Paper


TOPIC_ZH = {
    "recommender_systems": "推荐系统",
    "search_and_retrieval": "搜索与检索",
    "online_advertising": "广告算法",
    "llm4rec": "LLM4Rec",
    "generative_recommendation": "生成式推荐",
}

# CCF 第七版目录中与本项目领域相关的会议。等级只在论文明确标注录用时使用。
CCF_VENUES = {
    "SIGKDD": ("KDD", "A"),
    "KDD": ("KDD", "A"),
    "SIGIR": ("SIGIR", "A"),
    "THE WEB CONFERENCE": ("WWW", "A"),
    "WWW": ("WWW", "A"),
    "ACM MM": ("ACM MM", "A"),
    "ACMMM": ("ACM MM", "A"),
    "NEURIPS": ("NeurIPS", "A"),
    "ICML": ("ICML", "A"),
    "ICLR": ("ICLR", "A"),
    "AAAI": ("AAAI", "A"),
    "ACL": ("ACL", "A"),
    "CIKM": ("CIKM", "B"),
    "WSDM": ("WSDM", "B"),
    "RECSYS": ("RecSys", "B"),
    "IJCAI": ("IJCAI", "B"),
    "EMNLP": ("EMNLP", "B"),
}

NON_CCF_VENUES = {"ICTIR": "ICTIR"}

AFFILIATION_ZH = {
    "Meta": "Meta（脸书母公司）",
    "Tencent": "腾讯",
    "Tencent Inc.": "腾讯",
    "Alibaba": "阿里巴巴",
    "Taobao": "淘宝",
    "Taobao & Tmall Group of Alibaba": "阿里巴巴淘天集团",
    "ByteDance": "字节跳动",
    "Microsoft": "微软",
    "Amazon": "亚马逊",
    "Huawei": "华为",
    "Huawei Technologies": "华为",
    "Huawei Ireland Research Center": "华为爱尔兰研究中心",
    "JD": "京东",
    "Baidu": "百度",
    "Meituan": "美团",
    "Kuaishou": "快手",
    "Google": "谷歌",
    "University of Science and Technology of China": "中国科学技术大学",
    "Zhejiang University": "浙江大学",
    "Tsinghua University": "清华大学",
    "Peking University": "北京大学",
    "Fudan University": "复旦大学",
    "Anhui University": "安徽大学",
    "Beihang University": "北京航空航天大学",
    "Hangzhou Innovation Institute of BUAA": "北航杭州创新研究院",
    "Univ. of Illinois Chicago": "伊利诺伊大学芝加哥分校",
    "University of Illinois": "伊利诺伊大学",
    "University of Illinois Urbana-Champaign": "伊利诺伊大学厄巴纳-香槟分校",
    "University College Dublin": "都柏林大学",
}

SUBTOPIC_RULES = [
    ("生成式推荐", ("generative recommendation", "generative recommender")),
    ("生成式检索", ("generative retrieval",)),
    ("语义 ID", ("semantic id", "semantic ids")),
    ("因果召回", ("causal retrieval", "uplift")),
    ("长序列", ("long history", "long-history", "long sequence", "long-sequence")),
    ("序列推荐", ("sequential recommendation",)),
    ("多模态推荐", ("multi-modal", "multimodal")),
    ("广告精排", ("ad ranking", "ctr", "cvr")),
    ("搜索精排", ("search ranking", "pre-ranker", "pre-ranking")),
    ("特征交互", ("feature interaction", "feature ranking")),
    ("隐私推荐", ("privacy", "personalized-feature availability")),
    ("LLM Agent 推荐", ("language agent", "autonomous language agents")),
    ("Tokenization", ("tokenization", "tokenizer", "codebook")),
    ("用户召回", ("user reactivation", "returning user")),
]


def _accepted(comment: str) -> bool:
    return bool(re.search(r"\b(accepted|acceptance|to appear|published in)\b", comment, re.I))


def detect_venue(comment: str) -> tuple[str, str, str]:
    upper = comment.upper()
    if not _accepted(comment):
        return "arXiv", "预印本", ""
    for alias, (venue, rank) in CCF_VENUES.items():
        if re.search(rf"(?<![A-Z]){re.escape(alias)}(?:['’]?\d{{2,4}})?(?![A-Z])", upper):
            return venue, "已录用", rank
    for alias, venue in NON_CCF_VENUES.items():
        if re.search(rf"(?<![A-Z]){re.escape(alias)}(?:['’]?\d{{2,4}})?(?![A-Z])", upper):
            return venue, "已录用", "N"
    return "其他会议", "已录用", "N"


def translate_affiliations(values: list[str]) -> list[str]:
    translated = [AFFILIATION_ZH.get(value.strip(), value.strip()) for value in values if value.strip()]
    return list(dict.fromkeys(translated))[:6]


def infer_model_name(title: str, abstract: str) -> str:
    prefix = title.split(":", 1)[0].strip()
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9-]{1,15}", prefix):
        return prefix
    generic_acronyms = {"AI", "CTR", "CVR", "FFT", "GR", "ID", "LLM", "LLMS", "SR", "SID"}
    uppercase_proposal = re.search(r"\b(?:propose|present|introduce)\s+(?:the\s+)?([A-Z][A-Z0-9-]{2,15})\b", abstract)
    if uppercase_proposal and uppercase_proposal.group(1) not in generic_acronyms:
        return uppercase_proposal.group(1)
    for candidate in re.findall(r"\(([A-Z][A-Za-z0-9-]{2,15})\)", abstract):
        if candidate.upper() not in generic_acronyms:
            return candidate
    patterns = [
        r"\b(?:propose|present|introduce)\s+(?:the\s+)?([A-Z][A-Za-z0-9-]{2,15})\b",
        r"\b([A-Z][A-Z0-9-]{2,15})\s+(?:framework|model|module)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, abstract)
        if match:
            return match.group(1)
    for candidate in re.findall(r"\b([A-Z][A-Z0-9-]{3,15})\b", abstract):
        if candidate not in generic_acronyms:
            return candidate
    return ""


def infer_subtopics(title: str, abstract: str, topic_zh: str) -> list[str]:
    text = f"{title} {abstract}".lower()
    labels = [label for label, terms in SUBTOPIC_RULES if any(term in text for term in terms)]
    if topic_zh and topic_zh not in labels:
        labels.insert(0, topic_zh)
    return labels[:4]


def enrich_paper_metadata(paper: Paper) -> Paper:
    paper.topic_zh = paper.topic_zh or TOPIC_ZH.get(paper.topic, paper.topic)
    paper.affiliations_zh = paper.affiliations_zh or translate_affiliations(paper.affiliations)
    paper.model_name = paper.model_name or infer_model_name(paper.title, paper.abstract)
    inferred = infer_subtopics(paper.title, paper.abstract, paper.topic_zh)
    paper.subtopics_zh = list(dict.fromkeys(paper.subtopics_zh + inferred))[:4]
    paper.venue_name, paper.venue_status_zh, paper.ccf_rank = detect_venue(paper.comment)
    return paper


def enrich_record(record: dict) -> dict:
    defaults = {
        "arxiv_id": "",
        "title": "",
        "abstract": "",
        "authors": [],
        "categories": [],
        "published_at": "",
        "updated_at": "",
        "abs_url": "",
        "pdf_url": "",
    }
    normalized = {**defaults, **record}
    known = set(Paper.__dataclass_fields__)
    paper = Paper(**{key: value for key, value in normalized.items() if key in known})
    enrich_paper_metadata(paper)
    if paper.venue_status_zh == "预印本" and any(term in paper.quality_signal_zh for term in ("接收", "录用")):
        paper.quality_signal_zh = "arXiv 元数据未确认会议状态；按相关性、实验与工业信号综合入选。"
    if paper.ccf_rank == "B":
        paper.quality_signal_zh = paper.quality_signal_zh.replace("顶级会议", "CCF B 类会议")
    return {**record, **paper.to_dict()}
