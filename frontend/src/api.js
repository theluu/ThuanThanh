async function req(path, opts = {}) {
  const res = await fetch(`/api${path}`, { headers: { 'Content-Type': 'application/json' }, ...opts })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText)
  return res.json()
}

export const api = {
  health: () => req('/health'),
  startRun: (request) => req('/runs', { method: 'POST', body: JSON.stringify({ request }) }),
  getRun: (id) => req(`/runs/${id}`),
  approve: (id, approved) => req(`/runs/${id}/approval`, { method: 'POST', body: JSON.stringify({ approved }) }),
  prices: (includeEval) => req(`/prices?include_eval=${includeEval}`),
}
