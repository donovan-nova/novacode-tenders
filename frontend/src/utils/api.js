const API_BASE = process.env.REACT_APP_API_URL || "";

export async function fetchTenders(params = {}) {
  const query = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null))
  ).toString();
  const res = await fetch(`${API_BASE}/api/tenders/?${query}`);
  if (!res.ok) throw new Error("Failed to fetch tenders");
  return res.json();
}

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/api/stats/`);
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function fetchSources() {
  const res = await fetch(`${API_BASE}/api/sources/`);
  if (!res.ok) throw new Error("Failed to fetch sources");
  return res.json();
}

export async function fetchAlerts() {
  const res = await fetch(`${API_BASE}/api/alerts/`);
  if (!res.ok) throw new Error("Failed to fetch alerts");
  return res.json();
}

export async function createAlert(keyword) {
  const res = await fetch(`${API_BASE}/api/alerts/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keyword }),
  });
  return res.json();
}

export async function deleteAlert(id) {
  const res = await fetch(`${API_BASE}/api/alerts/${id}`, { method: "DELETE" });
  return res.json();
}

export async function triggerSync() {
  const res = await fetch(`${API_BASE}/api/tenders/sync`, { method: "POST" });
  return res.json();
}

export async function rescoreTender(id) {
  const res = await fetch(`${API_BASE}/api/tenders/${id}/rescore`, { method: "POST" });
  return res.json();
}
