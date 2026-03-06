import { Bar, CartesianGrid, Cell, ComposedChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

type CandlePoint = {
  label: string
  open: number
  close: number
}

type Props = {
  points: CandlePoint[]
  height?: number
}

type CandleChartRow = {
  label: string
  open: number
  close: number
  wickRange: [number, number]
  bodyRange: [number, number]
  color: string
  variation: number
}

const UP_COLOR = '#22c55e'
const DOWN_COLOR = '#ef4444'
const FLAT_COLOR = '#facc15'

function toRows(points: CandlePoint[]): CandleChartRow[] {
  if (points.length === 0) {
    return []
  }

  return points.map((point, index) => {
    const previousClose = index === 0 ? point.open : points[index - 1].close
    const open = Number.isFinite(point.open) ? point.open : previousClose
    const close = point.close
    const low = Math.min(open, close)
    const high = Math.max(open, close)
    const color = close > open ? UP_COLOR : close < open ? DOWN_COLOR : FLAT_COLOR

    return {
      label: point.label,
      open,
      close,
      wickRange: [low, high],
      bodyRange: [open, close],
      color,
      variation: close - open,
    }
  })
}

export function PriceCandlesChart({ points, height = 360 }: Props) {
  const rows = toRows(points)

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
        <XAxis dataKey="label" stroke="#a1a1aa" minTickGap={24} />
        <YAxis stroke="#a1a1aa" domain={["auto", "auto"]} />
        <Tooltip
          contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 12 }}
          formatter={(value, _name, item) => {
            const payload = item.payload as CandleChartRow
            const numericValue = Number(Array.isArray(value) ? value[1] : value)
            return [
              `${numericValue.toFixed(4)}`,
              item.dataKey === 'bodyRange'
                ? `Fechamento (${payload.variation >= 0 ? '+' : ''}${payload.variation.toFixed(4)})`
                : 'Faixa',
            ]
          }}
          labelFormatter={(label, payload) => {
            const row = payload?.[0]?.payload as CandleChartRow | undefined
            if (!row) return label
            return `${label} | Abertura ${row.open.toFixed(4)} | Fechamento ${row.close.toFixed(4)}`
          }}
        />
        <Bar dataKey="wickRange" barSize={3} radius={2} isAnimationActive={false}>
          {rows.map((row) => (
            <Cell key={`${row.label}-wick`} fill={row.color} />
          ))}
        </Bar>
        <Bar dataKey="bodyRange" barSize={12} radius={3} isAnimationActive={false}>
          {rows.map((row) => (
            <Cell key={`${row.label}-body`} fill={row.color} />
          ))}
        </Bar>
      </ComposedChart>
    </ResponsiveContainer>
  )
}
