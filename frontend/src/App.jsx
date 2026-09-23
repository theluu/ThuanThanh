import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from './api'
import ForecastChart from './ForecastChart'
import Pipeline from './Pipeline'
import Trace from './Trace'

const DEFAULT_REQUEST = 'Phân tích thị trường LNG 2024–2025 và dự báo giá JKM tháng kế tiếp'

export default function App() {
  const [request, setRequest] = useState(DEFAULT_REQUEST)
  const [runId, setRunId] = useState(null)
  const [run, setRun] = useState(null)
  const [prices, setPrices] = useState(null)
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('chart')
  const [pollKey, setPollKey] = useState(0) // bump to restart polling after approval
  const [deciding, setDeciding] = useState(false)

  useEffect(() => { api.health().then(setHealth).catch(() => setError('Không kết nối được máy chủ API. Kiểm tra backend đang chạy.')) }, [])

  useEffect(() => {
    if (!runId) return
    let stop = false
    const tick = async () => {
      try {
        const r = await api.getRun(runId)
        if (stop) return
        setRun(r)
        if (['completed', 'failed', 'waiting_approval'].includes(r.status)) return
      } catch (e) { setError(e.message) }
      if (!stop) setTimeout(tick, 1200)
    }
    tick()
    return () => { stop = true }
  }, [runId, pollKey])

  useEffect(() => {
    if (run?.status === 'completed') api.prices(runId).then(setPrices).catch((e) => setError(e.message))
  }, [runId, run?.status, run?.result?.external_approved])

  const start = async (e) => {
    e.preventDefault()
    setError(''); setRun(null); setPrices(null)
    try { setRunId((await api.startRun(request)).run_id) } catch (err) { setError(err.message) }
  }

  const decide = async (approved) => {
    setDeciding(true)
    try {
      await api.approve(runId, approved)
      setRun({ ...run, status: 'running', pending_approval: null })
      setPollKey((k) => k + 1)
    } catch (err) { setError(err.message) } finally { setDeciding(false) }
  }

  const busy = run && (run.status === 'running' || run.status === 'waiting_approval')

  return (
    <>
      <header className="masthead">
        <div className="wrap masthead-inner">
          <div className="brand">
            <svg viewBox="0 0 32 32" width="30" height="30" aria-hidden="true"><path d="M16 4c5 6 7.5 10.5 7.5 14.5a7.5 7.5 0 0 1-15 0C8.5 14.5 11 10 16 4z" fill="#0C9DB0" /></svg>
            <div>
              <p className="brand-name">LNG Desk</p>
              <p className="brand-sub">Nhóm agent phân tích và dự báo giá JKM</p>
            </div>
          </div>
          <p className={`llm ${health?.llm ? 'on' : ''}`}>{health ? (health.llm ? `LLM: ${health.providers.join(' → ')}` : 'Chế độ không LLM') : 'Đang kết nối…'}</p>
        </div>
        <form className="wrap ask" onSubmit={start}>
          <label htmlFor="req" className="sr-only">Yêu cầu cho nhóm agent</label>
          <input id="req" maxLength={500} value={request} onChange={(e) => setRequest(e.target.value)} />
          <button className="btn btn-cryo" disabled={busy || !request.trim()}>{busy ? 'Nhóm đang làm việc…' : 'Giao việc cho nhóm'}</button>
        </form>
      </header>

      <main className="wrap">
        {error && <p className="error" role="alert">{error}</p>}

        <Pipeline run={run} onDecide={decide} deciding={deciding} />

        {!run && (
          <p className="intro">
            Giao một yêu cầu, sáu trạm trên đường ống sẽ lần lượt xử lý: lập kế hoạch, nạp dữ liệu 2024–2025, phân tích, dựng mô hình và viết báo cáo dự báo tháng 01/2026.
            Trước khi chạm vào dữ liệu 2026 ở cơ sở dữ liệu khác, dòng chảy sẽ dừng ở van để chờ bạn cho phép.
          </p>
        )}

        {run?.status === 'completed' && run.result && <Manifest result={run.result} />}

        {run && (
          <div className="desk">
            <section className="panel log" aria-labelledby="log-h">
              <h2 id="log-h">Nhật ký agent <span className="count">{run.steps.length} bước</span></h2>
              <Trace steps={run.steps} />
            </section>
            <section className="panel output" aria-labelledby="out-h">
              <div className="output-head">
                <h2 id="out-h">Kết quả</h2>
                {run.status === 'completed' && (
                  <div className="tabs" role="tablist">
                    <button role="tab" aria-selected={tab === 'chart'} onClick={() => setTab('chart')}>Biểu đồ dự báo</button>
                    <button role="tab" aria-selected={tab === 'report'} onClick={() => setTab('report')}>Báo cáo</button>
                  </div>
                )}
              </div>
              {run.status === 'completed' ? (
                tab === 'chart' ? <ForecastChart prices={prices} result={run.result} /> : <article className="report"><ReactMarkdown remarkPlugins={[remarkGfm]}>{run.report}</ReactMarkdown></article>
              ) : run.status === 'failed' ? (
                <p className="error">Lần chạy dừng lại: {run.error}. Kiểm tra cơ sở dữ liệu rồi giao việc lại.</p>
              ) : run.status === 'waiting_approval' ? (
                <p className="empty">Dòng chảy đang dừng ở van. Chọn cho phép hoặc từ chối kết nối để nhóm làm tiếp.</p>
              ) : (
                <p className="empty">Báo cáo và biểu đồ sẽ hiện ở đây khi Report Writer hoàn tất.</p>
              )}
            </section>
          </div>
        )}
      </main>
    </>
  )
}

function Manifest({ result }) {
  const mr = result.model_results
  const bt = result.backtest
  const [y, m] = (result.forecast?.[0]?.Date || '').split('-')
  const month = `${m}/${y}`
  const items = [
    { k: `Dự báo trung bình ${month}`, v: mr.forecast_mean.toFixed(2), u: 'USD/MMBtu', tone: 'cryo' },
    { k: 'Mô hình được chọn', v: mr.chosen, u: `MAE kiểm định chéo ${mr.cv.summary[mr.chosen].MAE.toFixed(2)}` },
    bt
      ? { k: 'Sai số thực tế tháng 01/2026', v: `${bt.metrics.MAPE.toFixed(1)}%`, u: `MAPE, MAE ${bt.metrics.MAE.toFixed(2)}`, tone: 'brick' }
      : { k: 'Kiểm định ngoài mẫu', v: 'Bỏ qua', u: 'Kết nối DB ngoài bị từ chối' },
    bt
      ? { k: 'Ngày nằm trong khoảng 80%', v: `${Math.round(bt.interval_coverage * 100)}%`, u: `${bt.n_days} phiên`, tone: 'valve' }
      : { k: 'Số phiên dự báo', v: result.forecast.length, u: 'ngày giao dịch' },
  ]
  return (
    <dl className="manifest">
      {items.map((it) => (
        <div key={it.k} className={`mf tone-${it.tone || 'hull'}`}>
          <dt>{it.k}</dt>
          <dd><span className="mf-v">{it.v}</span><span className="mf-u">{it.u}</span></dd>
        </div>
      ))}
    </dl>
  )
}
