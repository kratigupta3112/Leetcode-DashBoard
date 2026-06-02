const DATA_URL = "../data/dashboard_data.json";

const state = {
  rows: [],
  filtered: [],
  sortKey: "date",
  sortDir: "desc",
  page: 1,
  pageSize: 25,
  query: "",
};

const els = {
  search: document.getElementById("search"),
  clear: document.getElementById("clear-search"),
  body: document.getElementById("table-body"),
  count: document.getElementById("result-count"),
  pagination: document.getElementById("pagination"),
  pageSize: document.getElementById("page-size"),
  updated: document.getElementById("last-updated"),
};

function median(values) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function formatDate(iso) {
  const date = new Date(iso);
  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatNum(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Number(value).toFixed(Number(value) % 1 ? 2 : 0);
}

function parseRange(token) {
  if (token.endsWith("+")) {
    return { min: Number(token.slice(0, -1)), max: Infinity };
  }
  if (token.includes("-")) {
    const [min, max] = token.split("-").map(Number);
    return { min, max };
  }
  const exact = Number(token);
  return { min: exact, max: exact };
}

function matchesRange(value, rangeToken) {
  if (value === null || value === undefined) return false;
  const { min, max } = parseRange(rangeToken);
  return value >= min && value <= max;
}

function tokenizeQuery(query) {
  const tokens = [];
  let current = "";
  let depth = 0;
  for (const char of query.trim()) {
    if (char === "(") depth += 1;
    if (char === ")") depth = Math.max(0, depth - 1);
    if ((char === " " || char === "\t") && depth === 0) {
      if (current) tokens.push(current);
      current = "";
      continue;
    }
    current += char;
  }
  if (current) tokens.push(current);
  return tokens;
}

function evalClause(row, clause) {
  const match = clause.match(/^(\w+):(.+)$/i);
  if (!match) return true;
  const field = match[1].toLowerCase();
  const value = match[2].trim();
  const fieldMap = {
    company: "company",
    role: "role",
    location: "location",
    yoe: "yoe",
    base: "base",
    ctc: "total",
    total: "total",
  };
  const key = fieldMap[field];
  if (!key) return true;

  const rowValue = row[key];
  if (key === "yoe" || key === "base" || key === "total") {
    return matchesRange(Number(rowValue), value);
  }
  return String(rowValue || "")
    .toLowerCase()
    .includes(value.toLowerCase());
}

function evalExpression(row, expression) {
  const parts = expression.split(/\s+OR\s+/i);
  if (parts.length > 1) {
    return parts.some((part) => evalExpression(row, part.trim()));
  }
  const andParts = expression.split(/\s+AND\s+/i);
  return andParts.every((part) => evalClause(row, part.trim()));
}

function applyFilters() {
  const query = state.query.trim();
  if (!query) {
    state.filtered = [...state.rows];
    return;
  }
  const groups = query.split(/\s+OR\s+/i);
  state.filtered = state.rows.filter((row) =>
    groups.some((group) => evalExpression(row, group.trim()))
  );
}

function applySort() {
  const { sortKey, sortDir } = state;
  const factor = sortDir === "asc" ? 1 : -1;
  state.filtered.sort((a, b) => {
    if (sortKey === "date") {
      return factor * (new Date(a.date) - new Date(b.date));
    }
    const av = a[sortKey];
    const bv = b[sortKey];
    if (av === bv) return 0;
    if (av === null || av === undefined) return 1;
    if (bv === null || bv === undefined) return -1;
    return factor * (av - bv);
  });
}

function renderTable() {
  applySort();
  const start = (state.page - 1) * state.pageSize;
  const pageRows = state.filtered.slice(start, start + state.pageSize);

  els.count.textContent = `${state.filtered.length} entries`;

  if (!pageRows.length) {
    els.body.innerHTML = `<tr><td colspan="7" class="empty">No matching offers</td></tr>`;
    renderPagination();
    return;
  }

  els.body.innerHTML = pageRows
    .map((row, index) => {
      const location = row.location ? ` · ${row.location}` : "";
      return `
        <tr>
          <td>${start + index + 1}</td>
          <td class="num"><a href="https://leetcode.com/discuss/post/${row.id}" target="_blank" rel="noopener">${row.id}</a></td>
          <td class="company-cell">
            <strong>${escapeHtml(row.company)}</strong>
            <small>${formatDate(row.date)}${escapeHtml(location)}</small>
          </td>
          <td>${escapeHtml(row.role)}</td>
          <td class="num">${formatNum(row.yoe)}</td>
          <td class="num">${formatNum(row.total)}</td>
          <td class="num">${formatNum(row.base)}</td>
        </tr>`;
    })
    .join("");

  renderPagination();
}

function renderPagination() {
  const totalPages = Math.max(1, Math.ceil(state.filtered.length / state.pageSize));
  state.page = Math.min(state.page, totalPages);

  const buttons = [];
  buttons.push(`<button data-page="prev" ${state.page === 1 ? "disabled" : ""}>‹</button>`);
  for (let i = 1; i <= totalPages; i += 1) {
    if (i === 1 || i === totalPages || Math.abs(i - state.page) <= 1) {
      buttons.push(
        `<button data-page="${i}" class="${i === state.page ? "active" : ""}">${i}</button>`
      );
    } else if (i === 2 || i === totalPages - 1) {
      buttons.push(`<span>…</span>`);
    }
  }
  buttons.push(
    `<button data-page="next" ${state.page === totalPages ? "disabled" : ""}>›</button>`
  );
  els.pagination.innerHTML = buttons.join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function refresh() {
  applyFilters();
  state.page = 1;
  renderTable();
}

async function loadData() {
  const response = await fetch(DATA_URL);
  if (!response.ok) throw new Error(`Failed to load data (${response.status})`);
  state.rows = await response.json();
  state.filtered = [...state.rows];
  const latest = state.rows[0]?.date;
  els.updated.textContent = latest
    ? `Updated through ${formatDate(latest)}`
    : "No data yet — run salary-sync";
  refresh();
}

document.querySelectorAll("th.sortable").forEach((header) => {
  header.addEventListener("click", () => {
    const key = header.dataset.sort;
    if (state.sortKey === key) {
      state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
    } else {
      state.sortKey = key;
      state.sortDir = "desc";
    }
    renderTable();
  });
});

els.search.addEventListener("input", (event) => {
  state.query = event.target.value;
  refresh();
});

els.clear.addEventListener("click", () => {
  els.search.value = "";
  state.query = "";
  refresh();
});

els.pageSize.addEventListener("change", (event) => {
  state.pageSize = Number(event.target.value);
  state.page = 1;
  renderTable();
});

els.pagination.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-page]");
  if (!button) return;
  const action = button.dataset.page;
  const totalPages = Math.max(1, Math.ceil(state.filtered.length / state.pageSize));
  if (action === "prev") state.page = Math.max(1, state.page - 1);
  else if (action === "next") state.page = Math.min(totalPages, state.page + 1);
  else state.page = Number(action);
  renderTable();
});

loadData().catch((error) => {
  els.body.innerHTML = `<tr><td colspan="7" class="empty">${escapeHtml(
    error.message
  )}</td></tr>`;
});
