import { useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from './api'

const AGENTS = {
  Orchestrator: { color: '#6d5dfc', icon: '🧭' },
  'Data Engineer': { color: '#0e9f6e', icon: '🛠️' },
  Human: { color: '#e3a008', icon: '🙋' },
  'Data Analyst': { color: '#1c64f2', icon: '📊' },
  'Data Scientist': { color: '#d61f69', icon: '🧪' },
  'Report Writer': { color: '#7e3af2', icon: '📝' },
  System: { color: '#e02424', icon: '⚠️' },
}
const PIPELINE = ['Orchestrator', 'Data Engineer', 'Human', 'Data Analyst', 'Data Scientist', 'Report Writer']

export default function App() {
  const [request, setRequest] = useState('Phân tích thị trường LNG 2024-2025 và dự báo giá JKM tháng kế tiếp')
  const [runId, setRunId] = useState(null)
  const [run, setRun] = useState(null)
  const [prices, setPrices] = useState(null)
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('report')
  const [pollKey, setPollKey] = useState(0) // bump to restart polling after approval

  useEffect(() => { api.health().then(setHealth).catch((e) => setError(e.message)) }, [])

  useEffect(() => {
    if (!runId) return
    let stop = false
    const tick = async () => {
      try {
        const r = await api.getRun(runId)
        if (stop) return
        setRun(r)
        if (r.status === 'completed' || r.status === 'failed') return
      } catch (e) { setError(e.message) }
      if (!stop) setTimeout(tick, 1500)
    }
    tick()
    return () => { stop = true }
  }, [runId, pollKey])

  useEffect(() => {
    if (run?.status === 'completed') api.prices(!!run.result?.external_approved).then(setPrices)
  }, [run?.status])

  const start = async () => {
    setError(''); setRun(null); setPrices(null)
    try { setRunId((await api.startRun(request)).run_id) } catch (e) { setError(e.message) }
  }
  const decide = async (approved) => {
    try { await api.approve(runId, approved); setRun({ ...run, status: 'running', pending_approval: null }); setPollKey((k) => k + 1) }
    catch (e) { setError(e.message) }
  }

  const doneAgents = new Set(run?.steps?.map((s) => s.agent) || [])
  const busy = run && (run.status === 'running' || run.status === 'waiting_approval')

  return (
    <div className="page">
      <header>
        <h1>LNG Agent Team <span>· JKM analysis & next-month forecast</span></h1>
        <div className="muted">LLM: {health ? (health.llm ? 'OpenAI ✓' : 'fallback template') : '…'}</div>
      </header>

      <section className="card">
        <textarea value={request} onChange={(e) => setRequest(e.target.value)} rows={2} />
        <button onClick={start} disabled={busy}>{busy ? 'Đang chạy…' : '▶ Chạy team agent'}</button>
        {error && <div className="error">{error}</div>}
      </section>

      {run && (
        <>
          <section className="pipeline">
            {PIPELINE.map((a) => (
              <div key={a} className={`node ${doneAgents.has(a) ? 'done' : ''}`} style={{ '--c': AGENTS[a].color }}>
                <span>{AGENTS[a].icon}</span>{a}
              </div>
            ))}
            <div className={`status s-${run.status}`}>{run.status}</div>
          </section>

          {run.status === 'waiting_approval' && run.pending_approval && (
            <section className="card approval">
              <h3>🔐 Yêu cầu xác nhận kết nối cơ sở dữ liệu khác</h3>
              <p><b>{run.pending_approval.agent}</b> muốn kết nối: <code>{run.pending_approval.target}</code></p>
              <p className="muted">{run.pending_approval.reason}</p>
              <div className="row">
                <button onClick={() => decide(true)}>✅ Approve</button>
                <button className="ghost" onClick={() => decide(false)}>❌ Reject</button>
              </div>
            </section>
          )}

          <div className="grid">
            <section className="card trace">
              <h3>Trace ({run.steps.length} bước)</h3>
              {run.steps.map((s) => <Step key={s.id} s={s} />)}
            </section>
            <section className="card">
              {run.status === 'completed' ? (
                <>
                  <div className="tabs">
                    {['report', 'chart'].map((t) => <button key={t} className={tab === t ? '' : 'ghost'} onClick={() => setTab(t)}>{t === 'report' ? 'Báo cáo' : 'Biểu đồ'}</button>)}
                  </div>
                  {tab === 'chart' ? <Chart prices={prices} result={run.result} /> : <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{run.report}</ReactMarkdown></div>}
                </>
              ) : run.status === 'failed' ? <div className="error">{run.error}</div> : <p className="muted">Các agent đang làm việc… báo cáo sẽ hiện ở đây.</p>}
            </section>
          </div>
        </>
      )}
    </div>
  )
}

function Step({ s }) {
  const [open, setOpen] = useState(false)
  const a = AGENTS[s.agent] || AGENTS.System
  return (
    <div className="step" style={{ '--c': a.color }} onClick={() => setOpen(!open)}>
      <div><span className="badge">{a.icon} {s.agent}</span> {s.action}</div>
      <div className="muted small">{new Date(s.created_at).toLocaleTimeString()}</div>
      {open && <pre>{JSON.stringify(s.detail, null, 2)}</pre>}
    </div>
  )
}

function Chart({ prices, result }) {
  const data = useMemo(() => {
    if (!prices) return []
    const m = new Map()
    prices.train.slice(-120).forEach((p) => m.set(p.Date, { Date: p.Date, train: p.JKM }))
    ;(prices.eval || []).forEach((p) => m.set(p.Date, { ...(m.get(p.Date) || { Date: p.Date }), actual2026: p.JKM }))
    ;(result?.forecast || []).forEach((f) => m.set(f.Date, { ...(m.get(f.Date) || { Date: f.Date }), forecast: f.forecast, lower: f.lower, upper: f.upper }))
    return [...m.values()].sort((a, b) => a.Date.localeCompare(b.Date))
  }, [prices, result])
  if (!prices) return <p className="muted">Loading…</p>
  return (
    <ResponsiveContainer width="100%" height={420}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="Date" minTickGap={40} />
        <YAxis domain={['auto', 'auto']} />
        <Tooltip />
        <Legend />
        <Line isAnimationActive={false} dataKey="train" name="JKM lịch sử" stroke="#1c64f2" dot={false} />
        <Line isAnimationActive={false} dataKey="actual2026" name="Thực tế 2026 (DB ngoài)" stroke="#0e9f6e" dot={false} />
        <Line isAnimationActive={false} dataKey="forecast" name="Dự báo" stroke="#d61f69" strokeWidth={2} dot={false} />
        <Line isAnimationActive={false} dataKey="upper" name="Cận trên 80%" stroke="#d61f69" strokeDasharray="4 4" dot={false} />
        <Line isAnimationActive={false} dataKey="lower" name="Cận dưới 80%" stroke="#d61f69" strokeDasharray="4 4" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
