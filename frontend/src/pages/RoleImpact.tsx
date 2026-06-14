import { useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { useMetricsContext } from '../context/MetricsContext'
import type { Core22Method } from '../types/metrics'

const METHOD_ORDER = ['priorRound', 'rollingTop22', 'seasonTop22']

const tooltipStyle = {
  background: '#1e293b',
  border: '1px solid #334155',
  borderRadius: 8,
}

function deltaColor(v: number) {
  if (v <= -10) return '#ef4444'
  if (v < 0) return '#f97316'
  if (v > 5) return '#22c55e'
  return '#94a3b8'
}

function corrColor(v: number) {
  if (v <= -0.1) return '#ef4444'
  if (v < 0) return '#f97316'
  return '#94a3b8'
}

export default function RoleImpact() {
  const { data } = useMetricsContext()
  const impact = data.core22Impact
  const [methodId, setMethodId] = useState(METHOD_ORDER[0])

  const method = useMemo<Core22Method | undefined>(() => {
    if (!impact?.methods?.length) return undefined
    return impact.methods.find((m) => m.id === methodId) ?? impact.methods[0]
  }, [impact, methodId])

  if (!impact || !method) {
    return (
      <>
        <PageHeader
          title="Role impact"
          subtitle="Core-22 missed PVS vs winning (run ETL to populate metrics)."
        />
        <p className="text-slate-400 text-sm">No core22Impact data in metrics.json yet.</p>
      </>
    )
  }

  const corrChart = method.correlations
    .filter((r) => r.roleId !== 'total' && r.roleId !== 'mid' && r.roleId !== 'key_roles')
    .map((r) => ({ role: r.role, corrWin: r.corrWin }))

  const starChart = [...method.starMiss].sort((a, b) => a.deltaPp - b.deltaPp)

  return (
    <>
      <PageHeader
        title="Role impact on winning"
        subtitle={`Core-22 absences ${impact.fromSeason}–${impact.toSeason}: which positional misses correlate with losses.`}
      />

      <div className="flex flex-wrap gap-2 mb-6">
        {impact.methods.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => setMethodId(m.id)}
            className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
              method.id === m.id
                ? 'bg-afl-green text-afl-gold font-medium'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Team-rounds" value={method.teamRounds.toLocaleString()} />
        <StatCard
          label="Avg core missed"
          value={`${method.avgPlayersMissed.toFixed(1)} players`}
          hint={`${method.avgMissedPvs.toFixed(1)} PVS`}
        />
        <StatCard label="Win rate" value={`${(method.winRate * 100).toFixed(1)}%`} />
        <StatCard
          label="Archetype model R²"
          value={method.archetypeModelR2.toFixed(3)}
          hint="Win ~ role misses"
          accent="gold"
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mb-8">
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-1">Correlation with win</h3>
          <p className="text-xs text-slate-500 mb-4">More negative = missing that role hurts more</p>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={corrChart} layout="vertical" margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" domain={[-0.15, 0.05]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="role"
                  tick={{ fill: '#94a3b8', fontSize: 10 }}
                  width={100}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="corrWin" name="Corr (win)" radius={[0, 4, 4, 0]}>
                  {corrChart.map((entry) => (
                    <Cell key={entry.role} fill={corrColor(entry.corrWin)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-1">
            Star miss win-rate drop (PVS ≥ {impact.starPvsThreshold})
          </h3>
          <p className="text-xs text-slate-500 mb-4">Percentage-point change vs rounds without that star out</p>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={starChart} layout="vertical" margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="role"
                  tick={{ fill: '#94a3b8', fontSize: 10 }}
                  width={100}
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(value: number, name: string) => [
                    name === 'deltaPp' ? `${value.toFixed(1)} pp` : value,
                    name === 'deltaPp' ? 'Win rate change' : name,
                  ]}
                />
                <Bar dataKey="deltaPp" name="deltaPp" radius={[0, 4, 4, 0]}>
                  {starChart.map((entry) => (
                    <Cell key={entry.role} fill={deltaColor(entry.deltaPp)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mb-8">
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 overflow-x-auto">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Star absences detail</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-800">
                <th className="pb-2 pr-3">Role</th>
                <th className="pb-2 pr-3">Rounds</th>
                <th className="pb-2 pr-3">Win% miss</th>
                <th className="pb-2 pr-3">Win% ok</th>
                <th className="pb-2">Δ pp</th>
              </tr>
            </thead>
            <tbody>
              {starChart.map((row) => (
                <tr key={row.roleId} className="border-b border-slate-800/60">
                  <td className="py-2 pr-3">{row.role}</td>
                  <td className="py-2 pr-3 tabular-nums">{row.rounds}</td>
                  <td className="py-2 pr-3 tabular-nums">{(row.winWhenMiss * 100).toFixed(1)}%</td>
                  <td className="py-2 pr-3 tabular-nums">{(row.winOtherwise * 100).toFixed(1)}%</td>
                  <td
                    className={`py-2 tabular-nums font-medium ${
                      row.deltaPp < 0 ? 'text-red-400' : 'text-emerald-400'
                    }`}
                  >
                    {row.deltaPp > 0 ? '+' : ''}
                    {row.deltaPp.toFixed(1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Multivariate coefficients (win)</h3>
          <p className="text-xs text-slate-500 mb-3">
            Per 1 PVS missed, holding other roles constant. Key roles:{' '}
            <span className="text-afl-gold tabular-nums">{method.keyVsOther.keyRolesCoef.toFixed(4)}</span>
            {' · '}Other:{' '}
            <span className="text-afl-gold tabular-nums">{method.keyVsOther.otherRolesCoef.toFixed(4)}</span>
          </p>
          <dl className="space-y-1 text-sm max-h-64 overflow-y-auto">
            {[...method.coefficients]
              .sort((a, b) => a.coef - b.coef)
              .map((c) => (
                <div key={c.roleId} className="flex justify-between border-b border-slate-800 py-1.5">
                  <dt className="text-slate-400">{c.role}</dt>
                  <dd className="text-afl-gold tabular-nums">{c.coef.toFixed(4)}</dd>
                </div>
              ))}
          </dl>
        </div>
      </div>

      {method.id === 'priorRound' && method.yearly.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 mb-8">
          <h3 className="text-sm font-medium text-slate-300 mb-4">Year-by-year correlation (prior round 22)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={method.yearly} margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="season" tick={{ fill: '#94a3b8' }} />
                <YAxis domain={[-0.35, 0.1]} tick={{ fill: '#94a3b8' }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend />
                <Line type="monotone" dataKey="total" name="Total" stroke="#fbbf24" strokeWidth={2} dot />
                <Line type="monotone" dataKey="keyRoles" name="Key F/D" stroke="#22c55e" dot />
                <Line type="monotone" dataKey="mid" name="Mids" stroke="#60a5fa" dot />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-2">How to read this</h3>
        <p className="text-sm text-slate-400 leading-relaxed">{impact.interpretation}</p>
      </div>
    </>
  )
}
