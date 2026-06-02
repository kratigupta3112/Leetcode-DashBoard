const DATA_URL = "data/interview_data.json";

const state = {
  rows: [],
  filtered: [],
  selectedCompany: "All",
  query: "",
  page: 1,
  pageSize: 15,
};

const els = {
  stats: document.getElementById("stats"),
  companyList: document.getElementById("company-list"),
  search: document.getElementById("search-input"),
  clear: document.getElementById("search-clear"),
  body: document.getElementById("table-body"),
  count: document.getElementById("result-count"),
  pagination: document.getElementById("pagination"),
  chart: document.getElementById("company-chart"),
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function outcomeClass(outcome) {
  if (outcome === "offer") return "outcome-offer";
  if (outcome === "reject") return "outcome-reject";
  if (outcome === "ongoing") return "outcome-ongoing";
  return "outcome-unknown";
}

function companyCounts(rows) {
  const map = new Map();
  for (const row of rows) {
    const key = row.company || "Unknown";
    map.set(key, (map.get(key) || 0) + 1);
  }
  return [...map.entries()].sort((a, b) => b[1] - a[1]);
}

function renderChart(rows) {
  const top = companyCounts(rows).slice(0, 12);
  if (!top.length) {
    els.chart.innerHTML = '<p class="muted">No data yet — run interview sync.</p>';
    return;
  }
  const max = top[0][1];
  els.chart.innerHTML = top
    .map(([company, count]) => {
      const width = Math.max(8, Math.round((count / max) * 100));
      return `
        <button class="bar-row" data-company="${escapeHtml(company)}" type="button">
          <span class="bar-label">${escapeHtml(company)}</span>
          <span class="bar-track"><span class="bar-fill" style="width:${width}%"></span></span>
          <span class="bar-count">${count}</span>
        </button>`;
    })
    .join("");
}

function renderCompanyList(rows) {
  const counts = companyCounts(rows);
  const total = rows.length;
  const items = [
    `<button class="company-item active" data-company="All" type="button">All (${total})</button>`,
    ...counts.map(
      ([company, count]) =>
        `<button class="company-item" data-company="${escapeHtml(company)}" type="button">${escapeHtml(company)} (${count})</button>`
    ),
  ];
  els.companyList.innerHTML = items.join("");
  highlightCompany(state.selectedCompany);
}

function highlightCompany(company) {
  els.companyList.querySelectorAll(".company-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.company === company);
  });
}

function applyFilters() {
  const q = state.query.trim().toLowerCase();
  state.filtered = state.rows.filter((row) => {
    if (state.selectedCompany !== "All" && row.company !== state.selectedCompany) {
      return false;
    }
    if (!q) return true;
    const hay = `${row.company} ${row.role} ${row.title} ${row.outcome}`.toLowerCase();
    return hay.includes(q);
  });
}

function renderTable() {
  applyFilters();
  const start = (state.page - 1) * state.pageSize;
  const pageRows = state.filtered.slice(start, start + state.pageSize);
  els.count.textContent = `${state.filtered.length} experiences`;

  if (!pageRows.length) {
    els.body.innerHTML = `<tr><td colspan="6" class="empty">No matching interview experiences</td></tr>`;
    return;
  }

  els.body.innerHTML = pageRows
    .map(
      (row, i) => `
      <tr>
        <td>${start + i + 1}</td>
        <td><strong>${escapeHtml(row.company)}</strong></td>
        <td>${escapeHtml(row.role || "N/A")}</td>
        <td><span class="outcome-pill ${outcomeClass(row.outcome)}">${escapeHtml(row.outcome || "unknown")}</span></td>
        <td class="num">${row.rounds ?? "—"}</td>
        <td>
          <a href="${escapeHtml(row.url)}" target="_blank" rel="noopener">${escapeHtml(row.title).slice(0, 72)}${row.title.length > 72 ? "…" : ""}</a>
          <div class="row-meta">${formatDate(row.date)} · ↑${row.upvotes ?? 0}</div>
        </td>
      </tr>`
    )
    .join("");
}

function refresh() {
  state.page = 1;
  renderChart(state.rows);
  renderCompanyList(state.rows);
  renderTable();
}

async function loadData() {
  const response = await fetch(DATA_URL);
  if (!response.ok) throw new Error(`Failed to load interview data (${response.status})`);
  state.rows = await response.json();
  const companies = new Set(state.rows.map((r) => r.company)).size;
  els.stats.textContent = `${state.rows.length} experiences · ${companies} companies`;
  refresh();
}

els.search.addEventListener("input", (e) => {
  state.query = e.target.value;
  state.page = 1;
  renderTable();
});

els.clear.addEventListener("click", () => {
  els.search.value = "";
  state.query = "";
  renderTable();
});

els.companyList.addEventListener("click", (e) => {
  const btn = e.target.closest(".company-item");
  if (!btn) return;
  state.selectedCompany = btn.dataset.company;
  highlightCompany(state.selectedCompany);
  state.page = 1;
  renderTable();
});

els.chart.addEventListener("click", (e) => {
  const btn = e.target.closest(".bar-row");
  if (!btn) return;
  state.selectedCompany = btn.dataset.company;
  highlightCompany(state.selectedCompany);
  state.page = 1;
  renderTable();
});

loadData().catch((err) => {
  els.body.innerHTML = `<tr><td colspan="6" class="empty">${escapeHtml(err.message)}</td></tr>`;
});
