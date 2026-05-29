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
import { useFilters } from '../context/FilterContext'
import { useSeasonData } from '../hooks/useSeasonData'
import { useMetricsContext } from '../context/MetricsContext'

export default function ClubDetail() {
  const data = useSeasonData()
  const { filters } = useFilters()
  const { data: bundle } = useMetricsContext()

  const seasonKey = String(filters.season)
  const rounds =
    bundle.seasons?.[seasonKey]?.clubSeries?.[filters.club] ??
    data.clubUnavailableByRound

  const clubRanking = data.clubRankings.find((c) => c.club === filters.club)
  const totalUnavailable = rounds.reduce((s, r) => s + r.value, 0)
  const totalWins = rounds.reduce((s, r) => s + r.wins, 0)

  return (
    <>
      <PageHeader
        title={`${filters.club} — ${filters.season}`}
        subtitle="Rolling unavailable PVS, top-5 unavailable value, and wins by round."
      />
      <FilterBar />
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <StatCard label="Season unavailable PVS" value={totalUnavailable.toFixed(1)} accent="gold" />
        <StatCard
          label="Top-5 unavailable PVS"
          value={(clubRanking?.unavailableTop5 ?? 0).toFixed(1)}
          hint="Sum of highest-impact absences"
        />
        <StatCard label="Wins" value={totalWins} hint="From match results" accent="green" />
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-4">Unavailable PVS & wins by round</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rounds}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="round" tick={{ fill: '#94a3b8' }} />
              <YAxis yAxisId="left" tick={{ fill: '#94a3b8' }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: '#94a3b8' }} domain={[0, 1]} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="value"
                name="Unavailable PVS"
                stroke="#f5c518"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="top5"
                name="Top-5 PVS"
                stroke="#22d3ee"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="right"
                type="stepAfter"
                dataKey="wins"
                name="Win"
                stroke="#22c55e"
                strokeWidth={2}
                dot
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  )
}
