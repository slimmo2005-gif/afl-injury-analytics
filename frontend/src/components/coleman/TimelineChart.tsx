import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
import { formatHeight } from '../../lib/colemanStats'

export interface TimelinePoint {
  year: number
  height_cm: number
  player: string
  club: string
  goals: number
  kind: 'winner' | 'roy' | 'mckay' | 'forecast'
}

interface TimelineChartProps {
  points: TimelinePoint[]
}

const KIND_COLOR: Record<TimelinePoint['kind'], string> = {
  winner: '#64748b',
  roy: '#f5c518',
  mckay: '#22d3ee',
  forecast: '#34d399',
}

function TimelineTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ payload: TimelinePoint }>
}) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs shadow-lg">
      <p className="font-semibold text-slate-100">{p.player}</p>
      <p className="text-slate-400">{p.club} · {p.year}</p>
      <p className="text-slate-300 mt-1">{formatHeight(p.height_cm)}</p>
      <p className="text-slate-400">{p.goals} goals</p>
      {p.kind === 'forecast' && (
        <p className="text-emerald-400 mt-1">2026 challenger (season in progress)</p>
      )}
    </div>
  )
}

export default function TimelineChart({ points }: TimelineChartProps) {
  const byKind = (kind: TimelinePoint['kind']) => points.filter((p) => p.kind === kind)

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:p-6">
      <h3 className="text-sm font-medium text-slate-300 mb-1">Height over time</h3>
      <p className="text-xs text-slate-500 mb-4">
        Every Coleman Medallist with recorded height · highlights for Roy Park, Harry McKay, and Nick Watson
      </p>
      <div className="h-80 sm:h-96">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 12, right: 12, bottom: 12, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              type="number"
              dataKey="year"
              domain={['dataMin - 2', 'dataMax + 2']}
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              name="Year"
            />
            <YAxis
              type="number"
              dataKey="height_cm"
              domain={[160, 210]}
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              name="Height (cm)"
              unit=" cm"
            />
            <ZAxis range={[24, 24]} />
            <Tooltip content={<TimelineTooltip />} cursor={{ strokeDasharray: '3 3' }} />
            <Scatter name="Winners" data={byKind('winner')} fill={KIND_COLOR.winner} />
            <Scatter name="Roy Park" data={byKind('roy')} fill={KIND_COLOR.roy} shape="star" />
            <Scatter name="Harry McKay" data={byKind('mckay')} fill={KIND_COLOR.mckay} />
            <Scatter name="Nick Watson" data={byKind('forecast')} fill={KIND_COLOR.forecast} shape="diamond" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-400">
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-slate-500" /> Coleman winners</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-afl-gold rotate-45" /> Roy Park</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-cyan-400" /> Harry McKay</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-emerald-400 rotate-45" /> Nick Watson (2026)</span>
      </div>
    </div>
  )
}
