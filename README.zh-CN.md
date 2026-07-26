# 每日推荐系统 arXiv 论文 Agent

[English](README.md)

这是一个参考 [hermes-arxiv-agent](https://github.com/genggng/hermes-arxiv-agent) 设计的可配置论文自动化项目。它每天从 arXiv 检索论文，完成相关性筛选、质量评分、中文总结、历史去重，并把最多 20 篇论文推送到飞书。

默认领域包括推荐算法、搜索与排序、广告算法、LLM4Rec、生成式推荐、Semantic ID 和生成式检索。其他用户只需修改 `config.yaml`，就能换成自己的研究方向。

## 功能

- 在 `config.yaml` 配置 arXiv 分类、研究主题、关键词、排除词、重点机构和重点会议。
- 综合主题相关性、会议状态、机构、发布时间、代码数据和工业实验信号进行质量评分。
- 每次最多推送 20 篇，最终严格按照 arXiv 首次上传时间从近到远排列。
- 每篇包含：标题、链接、首次上传时间、最近更新时间、会议/发表状态、作者、单位、领域标签、中文摘要、实践价值和入选依据。
- 按 arXiv ID 持久化去重；只有飞书消息全部发送成功后，才写入已发送历史。
- 自动拆分飞书消息，避免 20 篇内容超过单条消息限制。
- 作者单位优先从 arXiv HTML 提取并使用有限并发；较慢的 PDF 回退可配置，默认关闭。
- GitHub Actions 每天北京时间 08:00 自动运行，也支持手动触发。
- 支持 OpenAI-compatible 接口，可配置模型和 API 地址。

## 快速部署

1. Fork 本仓库。
2. 修改 `config.yaml`，设置你的领域和关键词。
3. 在飞书群中创建自定义机器人并获取 Webhook 地址。
4. 打开 GitHub 仓库的 **Settings > Secrets and variables > Actions**，添加：

   - `FEISHU_WEBHOOK_URL`：飞书自定义机器人 Webhook。
   - `LLM_API_KEY`：`config.yaml` 中 OpenAI-compatible 服务对应的 API Key。

5. 启用 GitHub Actions，手动运行一次 **Daily paper digest** 验证配置。

定时任务在每天 `00:00 UTC` 运行，对应北京时间 `08:00`。

## 更换研究领域

通常只需要编辑 `config.yaml`：

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

程序先按质量分挑出最多 20 篇，再按 `published_at` 倒序排列，所以最终消息中最新上传的论文排在最前面。

## 如何定义“优质论文”

会议等级是重要信号，但不是硬门槛。已被 SIGIR、KDD、WWW、NeurIPS、ICML 等会议录用的论文会获得加分；优秀 arXiv 预印本如果具备扎实实验、线上部署、公开代码/数据、可信机构或明确技术创新，同样可以入选。

程序不会把普通 arXiv 预印本写成“已录用”。会议状态主要依据 arXiv comment 和论文首页，并在消息中保留原始状态描述。

## 防止重复推送

`data/sent_papers.json` 保存已经成功推送的 arXiv ID。每次运行会先排除这些论文；只有全部飞书消息发送成功，程序才原子更新历史文件。GitHub Actions 随后把新状态提交回仓库，因此第二天不会再次推送同一篇论文。

请在 **Settings > Actions > General > Workflow permissions** 中启用 **Read and write permissions**，否则 Action 无法提交去重历史。

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/..."
export LLM_API_KEY="..."
python -m daily_paper_agent --config config.yaml --dry-run --max-papers 3 --candidate-limit 20 --pdf-limit 5
python -m daily_paper_agent --config config.yaml
```

`--dry-run` 会生成 `data/latest.json`，但不会发送飞书消息，也不会修改去重历史。可选的数量参数只影响当前试跑，不会改写 `config.yaml`。

如果单位完整性比运行稳定性更重要，可设置 `schedule.pdf_fallback_enabled: true`。默认关闭时，缺少 HTML 的论文会明确标注“未可靠提取”，不会猜测作者单位。

## 测试

```bash
pip install -r requirements-dev.txt
pytest -q
```

## 安全

不要把飞书 Webhook 或模型 API Key 写入仓库。只使用 GitHub Actions Secrets 或本地环境变量。

## License

MIT
