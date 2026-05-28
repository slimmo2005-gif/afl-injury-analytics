import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import FilterBar from '../components/FilterBar'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import mock from '../data/mockMetrics.json'
import type { MockMetrics } from '../types/metrics'

const data = mock as MockMetrics

export default function ClubDetail() {
  const rounds = data.clubUnavailableByRound
  const totalUnavailable = rounds.reduce((s, r) => s + r.value, 0)

  return (
    <>
      <PageHeader
        title="Club detail"
        subtitle="Rolling unavailable player value, wins, and continuity for a single club."
      />
      <FilterBar />
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <StatCard label="Season unavailable PVS" value={totalUnavailable} accent="gold" />
        <StatCard label="Top-5 unavailable" value={58} hint="Sum of highest-impact absences" />
        <StatCard label="Lineup changes (avg)" value={9.2} hint="Week-to-week" accent="green" />
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-4">Unavailable value & wins by round</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rounds}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="round" tick={{ fill: '#94a3b8' }} />
              <YAxis yAxisId="left" tick={{ fill: '#94a3b8' }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: '#94a3b8' }} domain={[0, 1]} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="value" name="Unavailable PVS" stroke="#f5c518" strokeWidth={2} dot={false} />
              <Line yAxisId="right" type="stepAfter" dataKey="wins" name="Win (0/1)" stroke="#22c55e" strokeWidth={2} dot />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  )
}
