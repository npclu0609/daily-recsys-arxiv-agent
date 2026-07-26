---
name: manage-recsys-papers
description: Operate, configure, test, and troubleshoot the daily-recsys-arxiv-agent that discovers and ranks arXiv papers, summarizes them, deduplicates delivery, sends Feishu digests, and publishes a GitHub Pages archive. Use for requests to preview or immediately push papers, change research topics or quality rules, inspect sent-paper history, manage the 08:00 GitHub Actions schedule, rebuild the web archive, deploy a fork, or diagnose failed runs.
---

# Manage Recsys Papers

Manage the `daily-recsys-arxiv-agent` repository through natural-language requests. Keep GitHub Actions responsible for unattended daily scheduling; use this skill for setup, control, and maintenance.

## Locate The Project

1. Search the current workspace for `daily_paper_agent/`, `config.yaml`, and `pyproject.toml` in the same directory.
2. Prefer the user's existing checkout. Preserve unrelated and uncommitted changes.
3. If no checkout exists and the user asks to set up the agent, clone `https://github.com/npclu0609/daily-recsys-arxiv-agent.git` into a clearly named workspace directory.
4. Confirm the git remote and current branch before changing workflows or pushing.

## Choose The Workflow

### Preview Papers

Use preview mode by default when the user asks to test, inspect, or find papers without explicitly asking to send them:

```bash
python -m daily_paper_agent --config config.yaml --dry-run --max-papers 3 --candidate-limit 20 --pdf-limit 5
```

Read `data/latest.json` and report selected titles, scores, timestamps, and any warnings. Preview mode must not modify `data/sent_papers.json`.

### Send Papers Now

Treat a real Feishu push as an external side effect. Proceed only when the user's request clearly authorizes an immediate send. Before running, verify that `FEISHU_WEBHOOK_URL` and `LLM_API_KEY` are available without printing their values.

```bash
python -m daily_paper_agent --config config.yaml
python viewer/build_data.py
```

After success, confirm that `data/sent_papers.json` contains the new arXiv IDs and that `viewer/papers_data.json` is newest-first. Do not mark or manually insert papers as sent after a failed delivery.

### Change Research Coverage

Edit `config.yaml` conservatively. Preserve the schema and existing user choices. Typical fields are:

- `research.arxiv_categories`
- `research.topics`
- `research.exclude_keywords`
- `quality.preferred_institutions`
- `quality.preferred_venues`
- `quality.minimum_score`
- `schedule.max_papers_per_day`
- `schedule.lookback_days`

Run the config loader or a small dry run after editing. Keep CCF A or venue status as one quality signal rather than a hard acceptance rule; strong arXiv preprints may qualify through affiliations, experiments, code/data, novelty, or industrial evidence.

### Maintain Daily Scheduling

Inspect `.github/workflows/daily.yml`. The default cron is `0 0 * * *`, corresponding to 08:00 Asia/Shanghai. Remember that GitHub cron uses UTC.

For a deployed fork, verify:

- Actions are enabled.
- Workflow permissions allow repository writes.
- `FEISHU_WEBHOOK_URL` and `LLM_API_KEY` exist as Actions secrets.
- The workflow commits both deduplication state and Pages data.

Never place secret values in files, logs, commands that echo them, commits, or responses.

### Inspect Deduplication

Treat `data/sent_papers.json` as authoritative delivery history. Deduplicate by exact arXiv ID. Never remove IDs merely to make a test pass. If the user explicitly requests a resend, explain that removing an ID permits another delivery and obtain clear authorization before editing the history.

### Manage The Pages Archive

Run `python viewer/build_data.py` after legitimate state changes. The output must remain cumulative, unique by arXiv ID, and sorted by `published_at` descending.

Use `.github/workflows/pages.yml` for deployment. Enable Pages with GitHub Actions as the build source. Verify the workflow result and the repository's `https://<owner>.github.io/<repo>/` URL after deployment.

### Diagnose Failures

1. Inspect the latest workflow/job logs without exposing secrets.
2. Classify the failure as configuration, authentication, API/network, arXiv parsing, Feishu delivery, git push, or Pages deployment.
3. Reproduce with the smallest safe dry run when possible.
4. Fix only the relevant layer.
5. Run tests and a dry run before rerunning an external workflow.

## Verification

For code or configuration changes, run checks proportional to the change:

```bash
pytest -q
python viewer/build_data.py
git diff --check
```

For frontend changes, serve `viewer/` locally and verify desktop and mobile layouts, loading, filtering, favorites, empty state, and horizontal overflow. For workflow changes, inspect the completed GitHub Actions run.

Report what ran, whether anything was sent, how many papers were selected, whether deduplication state changed, and the relevant Pages or Actions URL.
