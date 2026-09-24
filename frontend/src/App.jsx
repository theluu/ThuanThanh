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
        if (['completed', 'declined', 'failed', 'waiting_approval'].includes(r.status)) return
      } catch (e) { setError(e.message) }
      if (!stop) setTimeout(tick, 1200)
    }
    tick()
    return () => { stop = true }
  }, [runId, pollKey])

  useEffect(() => {
    if (run?.status === 'completed') api.prices(runId).then(setPrices).catch((e) => setError(e.message))
  }, [runId, run?.status, run?.result?.external_approved])

  const startRun = async (text) => {
    setError(''); setRun(null); setPrices(null)
    try { setRunId((await api.startRun(text)).run_id) } catch (err) { setError(err.message) }
  }
  const start = (e) => { e.preventDefault(); startRun(request) }
  const tryExample = (text) => { setRequest(text); startRun(text) }

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
          <p className={`llm ${health?.llm ? 'on' : ''}`}>{health ? (health.llm ? `LLM: ${(health.providers ?? ['bật']).join(' → ')}` : 'Chế độ không LLM') : 'Đang kết nối…'}</p>
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
        {run?.status === 'completed' && run.result && !run.result.backtest && <NoBacktestNote result={run.result} />}
        {run?.status === 'completed' && run.result?.params?.notes?.length > 0 && (
          <ul className="notice notes" role="note">{run.result.params.notes.map((n) => <li key={n}>{n}</li>)}</ul>
        )}

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
              ) : run.status === 'declined' ? (
                <>
                  <article className={`report declined ${run.result?.kind === 'help' ? 'help' : ''}`}><ReactMarkdown remarkPlugins={[remarkGfm]}>{run.report}</ReactMarkdown></article>
                  {run.result?.examples?.length > 0 && (
                    <div className="examples">
                      {run.result.examples.map((ex) => (
                        <button key={ex} type="button" className="btn btn-quiet example" onClick={() => tryExample(ex)}>{ex}</button>
                      ))}
                    </div>
                  )}
                </>
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

const monthLabel = (result) => {
  const [y, m] = (result.forecast?.[0]?.Date || '').split('-')
  return `${m}/${y}`
}
const skipReason = (result) => {
  const p = result.params || {}
  if (p.backtest_available === false) return 'DB ngoài chỉ có giá thực tế 01–02/2026'
  return p.backtest === false ? 'Yêu cầu không cần backtest' : 'Kết nối DB ngoài bị từ chối'
}

function Manifest({ result }) {
  const mr = result.model_results
  const bt = result.backtest
  const month = monthLabel(result)
  const items = [
    { k: `Dự báo trung bình ${month}`, v: mr.forecast_mean.toFixed(2), u: bt ? 'USD/MMBtu · đã đối chiếu thực tế' : 'USD/MMBtu · chưa kiểm định', tone: 'cryo' },
    mr.band_low != null
      ? { k: 'Khoảng tin cậy 80%', v: `${mr.band_low.toFixed(2)} – ${mr.band_high.toFixed(2)}`, u: `mô hình ${mr.chosen}, MAE kiểm định chéo ${mr.cv.summary[mr.chosen].MAE.toFixed(2)}` }
      : { k: 'Mô hình được chọn', v: mr.chosen, u: `MAE kiểm định chéo ${mr.cv.summary[mr.chosen].MAE.toFixed(2)}` },
    bt
      ? { k: `Sai số thực tế tháng ${month}`, v: `${bt.metrics.MAPE.toFixed(1)}%`, u: `MAPE, MAE ${bt.metrics.MAE.toFixed(2)}`, tone: 'brick' }
      : { k: 'Kiểm định ngoài mẫu', v: 'Không có', u: skipReason(result), tone: 'warn' },
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

function NoBacktestNote({ result }) {
  return (
    <p className="notice" role="note">
      <strong>Dự báo chưa được kiểm định với giá thực tế.</strong> {skipReason(result)}, nên không có số liệu {monthLabel(result)} để đối chiếu.
      {result.params?.backtest_available !== false && ' Con số dự báo giống hệt lần chạy có kiểm định — dữ liệu 2026 chỉ dùng để chấm điểm dự báo, không dùng để huấn luyện mô hình.'}
    </p>
  )
}
