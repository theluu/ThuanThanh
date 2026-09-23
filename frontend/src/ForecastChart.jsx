import { useMemo } from 'react'
import { Area, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const C = { hull: '#0E2433', cryo: '#0C9DB0', valve: '#E89B0C', brick: '#C0432B', grid: '#D5DFE8', slate: '#5A6E80' }
const fmt = (v) => (typeof v === 'number' ? v.toFixed(3) : Array.isArray(v) ? `${v[0].toFixed(2)} – ${v[1].toFixed(2)}` : v)

export default function ForecastChart({ prices, result }) {
  const data = useMemo(() => {
    if (!prices) return []
    const m = new Map()
    const put = (d, patch) => m.set(d, { ...(m.get(d) || { Date: d }), ...patch })
    prices.train.slice(-130).forEach((p) => put(p.Date, { history: p.JKM }))
    ;(prices.eval || []).forEach((p) => put(p.Date, { actual: p.JKM }))
    ;(result?.forecast || []).forEach((f) => put(f.Date, { forecast: f.forecast, band: [f.lower, f.upper] }))
    return [...m.values()].sort((a, b) => a.Date.localeCompare(b.Date))
  }, [prices, result])

  if (!prices) return <p className="empty">Đang tải chuỗi giá…</p>
  const cutoff = prices.train.at(-1)?.Date
  return (
    <figure className="chart">
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={data} margin={{ top: 12, right: 8, bottom: 0, left: -8 }}>
          <CartesianGrid stroke={C.grid} vertical={false} />
          <XAxis dataKey="Date" minTickGap={48} tick={{ fill: C.slate, fontSize: 12 }} tickFormatter={(d) => d.slice(5)} />
          <YAxis domain={['auto', 'auto']} tick={{ fill: C.slate, fontSize: 12 }} width={48} />
          <Tooltip formatter={fmt} contentStyle={{ borderRadius: 6, borderColor: C.grid, fontSize: 13 }} />
          <Legend wrapperStyle={{ fontSize: 13 }} />
          <ReferenceLine x={cutoff} stroke={C.slate} strokeDasharray="2 4" label={{ value: 'Hết dữ liệu huấn luyện', fill: C.slate, fontSize: 11, position: 'insideTopLeft' }} />
          <Area isAnimationActive={false} dataKey="band" name="Khoảng tin cậy 80%" fill={C.valve} fillOpacity={0.18} stroke="none" />
          <Line isAnimationActive={false} dataKey="history" name="JKM 2024–2025" stroke={C.hull} strokeWidth={1.6} dot={false} />
          <Line isAnimationActive={false} dataKey="actual" name="Thực tế 2026" stroke={C.brick} strokeWidth={1.8} dot={false} />
          <Line isAnimationActive={false} dataKey="forecast" name="Dự báo" stroke={C.cryo} strokeWidth={2.6} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
      <figcaption>Giá JKM (USD/MMBtu). Đường thực tế 2026 chỉ xuất hiện khi bạn cho phép kết nối cơ sở dữ liệu ngoài.</figcaption>
    </figure>
  )
}
