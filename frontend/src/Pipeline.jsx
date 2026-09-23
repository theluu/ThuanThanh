import { STATIONS } from './agents'

/** The agent team drawn as a gas pipeline; the Human station is a valve that blocks flow until approved. */
export default function Pipeline({ run, onDecide, deciding }) {
  const steps = run?.steps || []
  const seen = new Set(steps.map((s) => s.agent))
  const decision = steps.find((s) => s.agent === 'Human')
  const rejected = decision?.action.startsWith('Rejected')
  const waiting = run?.status === 'waiting_approval'
  const finished = run?.status === 'completed' || run?.status === 'declined'
  const noBacktest = run?.result?.params?.backtest === false
  const failed = run?.status === 'failed'

  // Last station that has written to the trace; everything before it is done.
  const lastSeen = STATIONS.reduce((acc, st, i) => (seen.has(st.key) ? i : acc), -1)
  const stateOf = (st, i) => {
    if (st.valve) {
      if (waiting) return 'waiting'
      if (decision) return rejected ? 'closed' : 'open'
      return 'idle'
    }
    if (!seen.has(st.key)) return i === 0 && run && !failed ? 'active' : 'idle' // run started, first trace not written yet
    if (finished || waiting || i < lastSeen) return 'done'
    return failed ? 'failed' : 'active'
  }
  const states = STATIONS.map(stateOf)
  const filled = states.filter((s) => s === 'done' || s === 'open' || s === 'closed').length
  const flowing = run && !finished && !failed && !waiting

  return (
    <section className="pipeline" aria-label="Tiến trình nhóm agent">
      <div className="pipe" aria-hidden="true">
        <div className={`pipe-fill ${flowing ? 'flowing' : ''}`} style={{ width: `${(Math.max(filled - 0.5, 0) / (STATIONS.length - 1)) * 100}%` }} />
      </div>
      <ol className="stations">
        {STATIONS.map((st, i) => (
          <li key={st.key} className={`station s-${states[i]} ${st.valve ? 'is-valve' : ''}`}>
            <span className="joint" aria-hidden="true">{st.valve ? <ValveIcon /> : i + 1}</span>
            <span className="st-label">{st.label}</span>
            <span className="st-role">{st.valve && decision ? (rejected ? 'Đã từ chối — bỏ qua backtest' : 'Đã cho phép') : st.valve && noBacktest ? 'Không cần — không yêu cầu backtest' : st.role}</span>
            {st.valve && waiting && run.pending_approval && (
              <div className="valve-card" role="alertdialog" aria-labelledby="valve-title">
                <p id="valve-title" className="vc-title">Data Engineer muốn kết nối một cơ sở dữ liệu khác</p>
                <code className="vc-target">{run.pending_approval.target}</code>
                <p className="vc-reason">{run.pending_approval.reason}</p>
                <div className="vc-actions">
                  <button className="btn btn-valve" disabled={deciding} onClick={() => onDecide(true)}>Cho phép kết nối</button>
                  <button className="btn btn-quiet" disabled={deciding} onClick={() => onDecide(false)}>Từ chối</button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ol>
    </section>
  )
}

function ValveIcon() {
  return (
    <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M4 8v8l8-4-8-4zM20 8v8l-8-4 8-4z" fill="currentColor" stroke="none" />
      <path d="M12 12V5M8.5 5h7" />
    </svg>
  )
}
