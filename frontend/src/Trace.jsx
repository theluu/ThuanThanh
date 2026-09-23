import { useState } from 'react'
import { AGENT_TONE } from './agents'

/** Chronological log of every agent action; each entry expands to show the data it produced. */
export default function Trace({ steps }) {
  if (!steps.length) return <p className="empty">Nhật ký sẽ ghi lại từng bước khi các agent bắt đầu làm việc.</p>
  return (
    <ol className="trace">
      {steps.map((s) => <Entry key={s.id} s={s} />)}
    </ol>
  )
}

function Entry({ s }) {
  const [open, setOpen] = useState(false)
  const time = new Date(s.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  return (
    <li className={`entry tone-${AGENT_TONE[s.agent] || 'hull'}`}>
      <button className="entry-head" aria-expanded={open} onClick={() => setOpen(!open)}>
        <time>{time}</time>
        <span className="entry-agent">{s.agent}</span>
        <span className="entry-action">{s.action}</span>
      </button>
      {open && <pre className="entry-detail">{JSON.stringify(s.detail, null, 2)}</pre>}
    </li>
  )
}
