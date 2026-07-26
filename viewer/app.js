const state = { papers: [], favorites: new Set(JSON.parse(localStorage.getItem("paperFavorites") || "[]")) };
const $ = (id) => document.getElementById(id);
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const dateOnly = (value) => value ? value.slice(0, 10) : "未知日期";
const formatDate = (value) => value ? new Intl.DateTimeFormat("zh-CN", {year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(value)) : "未知";
const list = (value) => Array.isArray(value) && value.length ? value.join("、") : "未提供";

function venueLabel(paper) {
  if (["A", "B", "C"].includes(paper.ccf_rank)) return `${paper.venue_name} · CCF ${paper.ccf_rank} · ${paper.venue_status_zh}`;
  if (paper.ccf_rank === "N") return `${paper.venue_name} · 非 CCF 目录 · ${paper.venue_status_zh}`;
  return "arXiv 预印本";
}

function render() {
  const query = $("searchInput").value.trim().toLowerCase();
  const topic = $("topicFilter").value;
  const date = $("dateFilter").value;
  const favoritesOnly = $("favoriteOnly").checked;
  const direction = $("sortOrder").value === "asc" ? 1 : -1;
  const papers = state.papers.filter(paper => {
    const fields = [paper.title, paper.summary_zh, paper.abstract, paper.topic_zh, paper.model_name, paper.venue_name, ...(paper.subtopics_zh || []), ...(paper.authors || []), ...(paper.affiliations_zh || paper.affiliations || [])];
    const haystack = fields.join(" ").toLowerCase();
    const domains = [paper.topic_zh, ...(paper.subtopics_zh || [])];
    return (!query || haystack.includes(query)) && (!topic || domains.includes(topic)) && (!date || dateOnly(paper.published_at) === date) && (!favoritesOnly || state.favorites.has(paper.arxiv_id));
  }).sort((a, b) => direction * (a.published_at || "").localeCompare(b.published_at || ""));

  $("resultMeta").textContent = `显示 ${papers.length} / ${state.papers.length} 篇`;
  $("paperList").innerHTML = papers.map(paper => `
    <article class="paper">
      <div class="date"><strong>${escapeHtml(formatDate(paper.published_at))}</strong><span>首次上传</span>${paper.topic_zh ? `<span class="primaryTopic">${escapeHtml(paper.topic_zh)}</span>` : ""}</div>
      <div class="content">
        <h2><a href="${escapeHtml(paper.abs_url || "#")}" target="_blank" rel="noreferrer">${escapeHtml(paper.title)}</a></h2>
        <p class="meta">${escapeHtml(list(paper.authors))} · 更新于 ${escapeHtml(formatDate(paper.updated_at))}</p>
        <div class="paperBadges"><span class="venueBadge ${paper.ccf_rank ? "ranked" : ""}">${escapeHtml(venueLabel(paper))}</span>${(paper.subtopics_zh || []).map(tag => `<span class="techBadge">${escapeHtml(tag)}</span>`).join("")}</div>
        ${paper.model_name ? `<p class="modelName"><b>模型/方法</b>${escapeHtml(paper.model_name)}</p>` : ""}
        <p class="summaryZh">${escapeHtml(paper.summary_zh || paper.abstract || "暂无摘要")}</p>
        <div class="details">
          <div class="detail"><b>机构</b>${escapeHtml(list(paper.affiliations_zh || paper.affiliations))}</div>
          <div class="detail"><b>质量依据</b>${escapeHtml(paper.quality_signal_zh || "暂无")}${Number.isFinite(paper.quality_score) ? ` <span class="score">${paper.quality_score.toFixed(1)}</span>` : ""}</div>
          <div class="detail"><b>实践价值</b>${escapeHtml(paper.practical_value_zh || "暂无")}</div>
          <div class="detail"><b>arXiv ID</b>${escapeHtml(paper.arxiv_id)}</div>
        </div>
        <div class="links"><a href="${escapeHtml(paper.abs_url || "#")}" target="_blank" rel="noreferrer">摘要页 ↗</a><a href="${escapeHtml(paper.pdf_url || paper.abs_url || "#")}" target="_blank" rel="noreferrer">PDF ↗</a></div>
      </div>
      <button class="favorite ${state.favorites.has(paper.arxiv_id) ? "active" : ""}" data-id="${escapeHtml(paper.arxiv_id)}" aria-label="收藏论文" title="收藏论文">☆</button>
    </article>`).join("");
  $("emptyState").hidden = papers.length > 0;
  document.querySelectorAll(".favorite").forEach(button => button.addEventListener("click", () => toggleFavorite(button.dataset.id)));
}

function toggleFavorite(id) {
  state.favorites.has(id) ? state.favorites.delete(id) : state.favorites.add(id);
  localStorage.setItem("paperFavorites", JSON.stringify([...state.favorites]));
  render();
}

fetch("papers_data.json").then(response => {
  if (!response.ok) throw new Error("无法加载论文数据");
  return response.json();
}).then(data => {
  state.papers = data.papers || [];
  $("paperCount").textContent = state.papers.length;
  const domains = new Set();
  state.papers.forEach(paper => [paper.topic_zh, ...(paper.subtopics_zh || [])].filter(Boolean).forEach(item => domains.add(item)));
  [...domains].sort((a, b) => a.localeCompare(b, "zh-CN")).forEach(domain => $("topicFilter").add(new Option(domain, domain)));
  render();
}).catch(error => {
  $("resultMeta").textContent = error.message;
  $("emptyState").hidden = false;
});

["searchInput","topicFilter","dateFilter","sortOrder","favoriteOnly"].forEach(id => $(id).addEventListener(id === "searchInput" ? "input" : "change", render));
