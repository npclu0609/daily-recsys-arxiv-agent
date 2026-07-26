# Daily Recsys arXiv Agent

[中文文档](README.zh-CN.md)

A configurable daily arXiv paper agent inspired by [hermes-arxiv-agent](https://github.com/genggng/hermes-arxiv-agent). It discovers, quality-ranks, summarizes, deduplicates, and sends up to 20 recent papers to Feishu every day.

The default profile covers recommender systems, search and ranking, online advertising, LLM4Rec, generative recommendation, semantic IDs, and generative retrieval. All fields can be replaced in `config.yaml`.

## Features

- Configurable arXiv categories, topics, include terms, exclusions, institutions, and venues.
- Composite quality score based on relevance, venue evidence, institution signals, recency, reproducibility, and industrial evidence.
- Up to 20 papers per run, displayed from newest to oldest by arXiv publication time.
- Includes title, link, publication time, latest update time, status/venue, authors, affiliations, topic, Chinese summary, practical value, and selection rationale.
- Persistent arXiv-ID deduplication. State is updated only after every Feishu chunk succeeds.
- Feishu messages are split into configurable chunks to stay within message size limits.
- Author/affiliation enrichment prefers arXiv HTML and uses bounded concurrency. Slow PDF fallback is configurable and disabled by default.
- Runs at 08:00 Asia/Shanghai through GitHub Actions and supports manual dispatch.
- Deploys a cumulative, searchable GitHub Pages archive with date/topic filters and browser-local favorites.
- Includes an optional Codex Skill for natural-language setup, preview, configuration, immediate delivery, and troubleshooting.
- OpenAI-compatible LLM endpoint; the model and base URL are configurable.

## Quick Start

1. Fork this repository.
2. Edit `config.yaml` to define your research fields and keywords.
3. Create a Feishu custom bot and copy its webhook URL.
4. Add these repository secrets under **Settings > Secrets and variables > Actions**:

   - `FEISHU_WEBHOOK_URL`: Feishu custom-bot webhook URL.
   - `LLM_API_KEY`: API key for the OpenAI-compatible endpoint configured in `config.yaml`.

5. Enable GitHub Actions and run **Daily paper digest** manually once.

The scheduled workflow runs at `00:00 UTC`, which is `08:00 Asia/Shanghai`.

## Configure Another Research Field

Edit only `config.yaml`. For example:

```yaml
research:
  arxiv_categories: [cs.CV, cs.AI]
  topics:
    embodied_ai:
      - embodied ai
      - vision-language-action
      - robot policy
  exclude_keywords:
    - medical robotics

schedule:
  max_papers_per_day: 20
  lookback_days: 30
```

Selection first uses quality score, then the final digest is sorted by `published_at` descending. Therefore the newest selected paper always appears first.

## Quality Is Not Just Venue Tier

Conference acceptance is a strong signal, not a hard requirement. High-quality arXiv preprints can be selected when they show convincing experiments, production deployment, public code/data, strong affiliations, or a clear technical contribution. The agent must not label a preprint as accepted unless arXiv metadata or the paper itself supports that claim.

## Deduplication

`data/sent_papers.json` stores successfully delivered arXiv IDs. The workflow filters these IDs before ranking and writes new IDs only after all Feishu messages succeed. GitHub Actions commits the updated state to the repository, so scheduled runs do not resend previously delivered papers.

Keep the workflow permission **Read and write permissions** enabled under **Settings > Actions > General > Workflow permissions**.

## GitHub Pages Archive

The repository includes a static paper archive under `viewer/`. After every successful Feishu delivery, the daily workflow rebuilds `viewer/papers_data.json`; the Pages workflow then deploys it automatically.

1. Open **Settings > Pages** in your fork.
2. Under **Build and deployment > Source**, select **GitHub Actions**.
3. Run **Deploy paper archive** once, or push a change under `viewer/`.

Your site will be available at `https://<username>.github.io/<repository>/`. It supports full-text search, upload-date and topic filters, and favorites stored only in the current browser. The archive never changes delivery semantics: an item is added only after all Feishu messages succeed.

To preview locally:

```bash
python viewer/build_data.py
python viewer/run_viewer.py
```

Then open `http://127.0.0.1:8000`.

## Codex Skill

GitHub Actions remains the reliable daily scheduler. The bundled `manage-recsys-papers` Skill adds a natural-language control layer for Codex: it can safely preview papers, edit research coverage, run an explicitly requested immediate Feishu push, inspect deduplication history, rebuild Pages, and troubleshoot workflows.

Install it from a cloned repository:

```bash
cp -R skills/manage-recsys-papers ~/.codex/skills/
```

On Windows PowerShell:

```powershell
Copy-Item -Recurse skills\manage-recsys-papers "$HOME\.codex\skills\"
```

Restart Codex after installation, then invoke it explicitly with prompts such as:

```text
Use $manage-recsys-papers to preview today's top 5 papers without sending them.
Use $manage-recsys-papers to add multimodal recommendation to my topics.
Use $manage-recsys-papers to inspect yesterday's failed GitHub Actions run.
```

The Skill does not replace the 08:00 workflow. It operates and maintains the same agent project on demand.

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/..."
export LLM_API_KEY="..."
python -m daily_paper_agent --config config.yaml --dry-run --max-papers 3 --candidate-limit 20 --pdf-limit 5
python -m daily_paper_agent --config config.yaml
```

The dry run writes `data/latest.json` but does not send messages or modify deduplication state. The optional limit flags make first-run verification fast and do not change `config.yaml`.

Set `schedule.pdf_fallback_enabled: true` when affiliation completeness matters more than runtime stability. Without HTML or PDF fallback, the message explicitly marks affiliations as not reliably extracted.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Security

Never commit Feishu webhooks or API keys. Store them only as GitHub Actions secrets or local environment variables.

## License

MIT
