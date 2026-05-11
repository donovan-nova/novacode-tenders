import { useState, useEffect, useCallback } from "react";
import {
  fetchTenders, fetchStats, fetchSources, fetchAlerts,
  createAlert, deleteAlert, triggerSync, rescoreTender,
} from "./utils/api";
import "./App.css";

const COUNTRIES = [
  { code: "ZA", name: "South Africa" },
  { code: "KE", name: "Kenya" },
  { code: "ZM", name: "Zambia" },
  { code: "NG", name: "Nigeria" },
  { code: "GH", name: "Ghana" },
  { code: "UG", name: "Uganda" },
  { code: "TZ", name: "Tanzania" },
];

const CATEGORIES = [
  "AI & Automation", "Fintech", "ICT & Software",
  "Data & Analytics", "Consulting", "General",
];

function scoreClass(s) {
  if (s >= 80) return "score-high";
  if (s >= 50) return "score-med";
  return "score-low";
}

function daysLeft(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr) - new Date();
  return Math.ceil(d / (1000 * 60 * 60 * 24));
}

function formatValue(zar) {
  if (!zar) return null;
  if (zar >= 1_000_000) return `R${(zar / 1_000_000).toFixed(1)}M`;
  if (zar >= 1_000) return `R${(zar / 1_000).toFixed(0)}K`;
  return `R${zar}`;
}

// ── Stat Card ─────────────────────────────────
function StatCard({ label, value, accent }) {
  return (
    <div className="stat-card">
      <div className="stat-value">
        {value}
        {accent && <span className="stat-accent">{accent}</span>}
      </div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

// ── Tender Row ────────────────────────────────
function TenderRow({ tender, active, onClick }) {
  const days = daysLeft(tender.deadline);
  const urgent = days !== null && days <= 7;
  return (
    <div
      className={`tender-row${active ? " active" : ""}`}
      onClick={onClick}
    >
      <div className="tender-row-top">
        <div className="tender-title">{tender.title}</div>
        <div className={`score-badge ${scoreClass(tender.score)}`}>{tender.score}</div>
      </div>
      <div className="tender-dept">{tender.department}</div>
      <div className="tender-meta">
        <span className="tag tag-country">{tender.country}</span>
        <span className="tag">{tender.category}</span>
        {tender.value_raw && tender.value_raw !== "N/A" && (
          <span className="tag">{tender.value_raw}</span>
        )}
        {days !== null && (
          <span className={`deadline${urgent ? " urgent" : ""}`}>
            ⏱ {days}d left
          </span>
        )}
      </div>
    </div>
  );
}

// ── Detail Panel ──────────────────────────────
function DetailPanel({ tender, onRescore }) {
  const [rescoring, setRescoring] = useState(false);

  if (!tender) {
    return (
      <div className="detail-empty">
        <div className="detail-empty-icon">🔍</div>
        <div>Select a tender to view details</div>
      </div>
    );
  }

  const days = daysLeft(tender.deadline);
  const urgent = days !== null && days <= 7;

  const handleRescore = async () => {
    setRescoring(true);
    await onRescore(tender.id);
    setRescoring(false);
  };

  return (
    <div className="detail-inner">
      <div className={`score-badge large ${scoreClass(tender.score)}`}>
        {tender.score}
      </div>
      <h3 className="detail-title">{tender.title}</h3>

      <div className="detail-rows">
        {[
          ["Department", tender.department],
          ["Country", tender.country],
          ["Category", tender.category],
          ["Value", tender.value_raw],
          ["Reference", tender.reference],
          ["Source", tender.source],
          ["Published", tender.published],
          ["Deadline", tender.deadline ? `${tender.deadline}${days !== null ? ` (${days}d)` : ""}` : "—"],
        ].map(([label, val]) =>
          val ? (
            <div className={`detail-row${label === "Deadline" && urgent ? " urgent" : ""}`} key={label}>
              <span className="detail-label">{label}</span>
              <span className="detail-val">{val}</span>
            </div>
          ) : null
        )}
      </div>

      {tender.score_reason && (
        <div className="ai-section">
          <div className="ai-header">🤖 NovaCode AI Analysis</div>
          <p className="ai-text">{tender.score_reason}</p>
        </div>
      )}

      <div className="detail-actions">
        {tender.portal_url && (
          <a
            href={tender.portal_url}
            target="_blank"
            rel="noreferrer"
            className="btn btn-primary"
          >
            View on Portal ↗
          </a>
        )}
        <button
          className="btn"
          onClick={handleRescore}
          disabled={rescoring}
        >
          {rescoring ? "Scoring…" : "Re-score with AI"}
        </button>
      </div>
    </div>
  );
}

// ── Sources Tab ───────────────────────────────
function SourcesTab({ sources }) {
  const statusDot = (s) => {
    if (s === "active") return "🟢";
    if (s === "scheduled") return "🟡";
    return "⚪";
  };
  return (
    <div className="tab-content">
      <p className="tab-intro">
        Monitored procurement portals across Africa. SA uses the official OCDS API — structured, legal, free.
        Other countries use HTML scrapers that run every 6 hours.
      </p>
      <div className="sources-grid">
        {sources.map((s) => (
          <div className="source-card" key={s.id || s.name}>
            <div className="source-name">
              {statusDot(s.status)} {s.name}
            </div>
            <div className="source-meta">
              {s.country} · {s.tender_count || 0} tenders
            </div>
            <div className="source-sync">
              {s.last_synced ? `Last sync: ${s.last_synced.slice(0, 16)}` : "Not yet synced"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Alerts Tab ────────────────────────────────
function AlertsTab({ alerts, onAdd, onDelete }) {
  const [input, setInput] = useState("");

  const handleAdd = async () => {
    if (!input.trim()) return;
    await onAdd(input.trim());
    setInput("");
  };

  return (
    <div className="tab-content">
      <p className="tab-intro">
        Keywords that flag matching tenders as high-priority. The scorer uses these
        plus NovaCode's full capability profile.
      </p>
      <div className="alerts-list">
        {alerts.map((a) => (
          <div className="alert-row" key={a.id}>
            <span className="alert-keyword">🔔 {a.keyword}</span>
            <button className="btn-icon" onClick={() => onDelete(a.id)} title="Remove">✕</button>
          </div>
        ))}
      </div>
      <div className="alert-add">
        <input
          className="alert-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="Add keyword e.g. blockchain, SARS, insurance automation..."
        />
        <button className="btn btn-primary" onClick={handleAdd}>Add</button>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────
export default function App() {
  const [tab, setTab] = useState("tenders");
  const [tenders, setTenders] = useState([]);
  const [stats, setStats] = useState({});
  const [sources, setSources] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [filters, setFilters] = useState({
    search: "", country: "", category: "", min_score: "",
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filters.search) params.search = filters.search;
      if (filters.country) params.country = filters.country;
      if (filters.category) params.category = filters.category;
      if (filters.min_score) params.min_score = filters.min_score;

      const [t, s, src, al] = await Promise.all([
        fetchTenders(params),
        fetchStats(),
        fetchSources(),
        fetchAlerts(),
      ]);
      setTenders(t.tenders || []);
      setStats(s);
      setSources(src);
      setAlerts(al);
    } catch (e) {
      console.error("Load error:", e);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSync = async () => {
    setSyncing(true);
    await triggerSync();
    setTimeout(() => {
      loadData();
      setSyncing(false);
    }, 3000);
  };

  const handleRescore = async (id) => {
    const result = await rescoreTender(id);
    setTenders((prev) =>
      prev.map((t) =>
        t.id === id
          ? { ...t, score: result.score, score_reason: result.reason }
          : t
      )
    );
    if (selected?.id === id) {
      setSelected((prev) => ({ ...prev, score: result.score, score_reason: result.reason }));
    }
  };

  const handleAddAlert = async (kw) => {
    await createAlert(kw);
    const al = await fetchAlerts();
    setAlerts(al);
  };

  const handleDeleteAlert = async (id) => {
    await deleteAlert(id);
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  };

  const setFilter = (key, val) => {
    setFilters((prev) => ({ ...prev, [key]: val }));
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-brand">
          <div className="logo-mark">N{"{c}"}</div>
          <div>
            <div className="brand-name">Tender Intelligence</div>
            <div className="brand-sub">NovaCode · Africa Procurement Monitor</div>
          </div>
        </div>
        <div className="header-right">
          <span className="live-indicator">
            <span className="live-dot" />
            Live
          </span>
          <button
            className="btn btn-primary"
            onClick={handleSync}
            disabled={syncing}
          >
            {syncing ? "Syncing…" : "⟳ Refresh"}
          </button>
        </div>
      </header>

      {/* Tabs */}
      <nav className="tabs">
        {["tenders", "sources", "alerts"].map((t) => (
          <button
            key={t}
            className={`tab${tab === t ? " active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </nav>

      {tab === "tenders" && (
        <>
          {/* Controls */}
          <div className="controls">
            <div className="search-box">
              <input
                placeholder="Search tenders, departments…"
                value={filters.search}
                onChange={(e) => setFilter("search", e.target.value)}
              />
            </div>
            <select value={filters.country} onChange={(e) => setFilter("country", e.target.value)}>
              <option value="">All countries</option>
              {COUNTRIES.map((c) => (
                <option key={c.code} value={c.code}>{c.name}</option>
              ))}
            </select>
            <select value={filters.category} onChange={(e) => setFilter("category", e.target.value)}>
              <option value="">All categories</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <select value={filters.min_score} onChange={(e) => setFilter("min_score", e.target.value)}>
              <option value="">Any match</option>
              <option value="80">High match (80+)</option>
              <option value="50">Medium (50+)</option>
            </select>
          </div>

          {/* Stats */}
          <div className="stats-bar">
            <StatCard label="Active tenders" value={stats.total_active ?? "—"} />
            <StatCard label="Strong matches" value={stats.high_matches ?? "—"} accent="high" />
            <StatCard
              label="Total ZA value"
              value={stats.total_value_zar ? formatValue(stats.total_value_zar) : "—"}
            />
            <StatCard label="Closing this week" value={stats.closing_this_week ?? "—"} />
          </div>

          {/* Body */}
          <div className="body">
            <div className="tender-list">
              {loading ? (
                <div className="loading">Loading tenders…</div>
              ) : tenders.length === 0 ? (
                <div className="loading">No tenders found. Try refreshing or adjusting filters.</div>
              ) : (
                tenders.map((t) => (
                  <TenderRow
                    key={t.id}
                    tender={t}
                    active={selected?.id === t.id}
                    onClick={() => setSelected(t)}
                  />
                ))
              )}
            </div>
            <div className="detail-panel">
              <DetailPanel tender={selected} onRescore={handleRescore} />
            </div>
          </div>
        </>
      )}

      {tab === "sources" && <SourcesTab sources={sources} />}
      {tab === "alerts" && (
        <AlertsTab alerts={alerts} onAdd={handleAddAlert} onDelete={handleDeleteAlert} />
      )}
    </div>
  );
}
