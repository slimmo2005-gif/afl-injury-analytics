import { useMemo, useState } from 'react'
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
import { formatHeight, type TimelinePoint } from '../../lib/colemanStats'

interface TimelineChartProps {
  points: TimelinePoint[]
}

const KIND_COLOR: Record<TimelinePoint['kind'], string> = {
  coleman: '#64748b',
  leading_gk_medal: '#b45309',
  roy: '#f5c518',
  mckay: '#22d3ee',
  watson: '#34d399',
}

const KIND_LABEL: Record<TimelinePoint['kind'], string> = {
  coleman: 'Coleman Medallist (1955+)',
  leading_gk_medal: 'Leading Goalkicker Medallist (1897–1954)',
  roy: 'Roy Park · Leading Goalkicker Medallist',
  mckay: 'Harry McKay · Coleman Medallist',
  watson: 'Nick Watson · 2026 challenger',
}

function HitDot({
  cx,
  cy,
  payload,
  activeId,
  onSelect,
}: {
  cx?: number
  cy?: number
  payload?: TimelinePoint & { id: string }
  activeId: string | null
  onSelect: (p: TimelinePoint & { id: string }) => void
}) {
  if (cx == null || cy == null || !payload) return null
  const isActive = activeId === payload.id
  const isHighlight = payload.kind === 'roy' || payload.kind === 'mckay' || payload.kind === 'watson'
  const r = isActive ? 10 : isHighlight ? 8 : 5

  return (
    <g onClick={() => onSelect(payload)} style={{ cursor: 'pointer' }}>
      <circle cx={cx} cy={cy} r={16} fill="transparent" />
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill={KIND_COLOR[payload.kind]}
        stroke={isActive ? '#f8fafc' : '#0f172a'}
        strokeWidth={isActive ? 2.5 : 1}
        opacity={isActive ? 1 : 0.92}
      />
    </g>
  )
}

function TimelineTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ payload: TimelinePoint & { id: string } }>
}) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-xs shadow-xl max-w-[240px]">
      <p className="font-semibold text-slate-100">{p.player}</p>
      <p className="text-slate-400">{p.club} · {p.year}</p>
      <p className="text-slate-300 mt-1">{formatHeight(p.height_cm)}</p>
      <p className="text-slate-400">{p.goals} goals</p>
      <p className="text-slate-500 mt-1">{p.award}</p>
      {p.kind === 'watson' && (
        <p className="text-emerald-400 mt-1">2026 challenger (season in progress)</p>
      )}
    </div>
  )
}

export default function TimelineChart({ points }: TimelineChartProps) {
  const [activeId, setActiveId] = useState<string | null>(null)

  const data = useMemo(
    () => points.map((p) => ({ ...p, id: `${p.year}-${p.player}`, z: 1 })),
    [points],
  )

  const activePoint = data.find((p) => p.id === activeId) ?? null

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:p-6">
      <h3 className="text-sm font-medium text-slate-300 mb-1">Height over time</h3>
      <p className="text-xs text-slate-500 mb-4">
        Every league leading goalkicker with a recorded height. Grey dots are Coleman Medallists
        (1955+, including those recognised retrospectively in 2001). Amber dots are Leading
        Goalkicker Medallists (1897–1954). Tap or hover a dot for details.
      </p>
      <div className="h-80 sm:h-96">
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <ScatterChart margin={{ top: 12, right: 16, bottom: 12, left: 4 }}>
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
            <ZAxis type="number" dataKey="z" range={[120, 120]} />
            <Tooltip
              content={<TimelineTooltip />}
              cursor={{ strokeDasharray: '3 3', stroke: '#475569' }}
              isAnimationActive={false}
            />
            <Scatter
              data={data}
              isAnimationActive={false}
              shape={(props) => (
                <HitDot
                  {...props}
                  activeId={activeId}
                  onSelect={(p) => setActiveId(p.id)}
                />
              )}
              onMouseEnter={(d) => {
                const pt = d as TimelinePoint & { id: string }
                if (pt?.id) setActiveId(pt.id)
              }}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {activePoint && (
        <div className="mt-4 rounded-lg border border-slate-700 bg-slate-900/80 px-4 py-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-semibold text-slate-100">{activePoint.player}</p>
            <p className="text-sm text-slate-400">
              {activePoint.club} · {activePoint.year} · {activePoint.goals} goals
            </p>
            <p className="text-xs text-slate-500 mt-0.5">{activePoint.award}</p>
          </div>
          <div className="text-right">
            <p className="text-lg font-semibold text-slate-100 tabular-nums">
              {activePoint.height_cm} cm
            </p>
            <p className="text-xs text-slate-500">{KIND_LABEL[activePoint.kind]}</p>
          </div>
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-slate-500" /> Coleman Medallist (1955+)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-700" /> Leading Goalkicker Medallist (1897–1954)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-afl-gold" /> Roy Park
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" /> Harry McKay
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" /> Nick Watson (2026)
        </span>
      </div>
    </div>
  )
}
