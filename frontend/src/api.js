const TOKEN = import.meta.env.VITE_API_TOKEN // must match backend API_TOKEN when auth is enabled

async function req(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(TOKEN ? { 'X-API-Key': TOKEN } : {}) }
  const res = await fetch(`/api${path}`, { headers, ...opts })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText)
  return res.json()
}

export const api = {
  health: () => req('/health'),
  startRun: (request) => req('/runs', { method: 'POST', body: JSON.stringify({ request }) }),
  getRun: (id) => req(`/runs/${id}`),
  approve: (id, approved) => req(`/runs/${id}/approval`, { method: 'POST', body: JSON.stringify({ approved }) }),
  prices: (runId) => req(runId ? `/prices?run_id=${encodeURIComponent(runId)}` : '/prices'),
}
