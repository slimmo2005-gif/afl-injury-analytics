import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
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
import type { LadderPvsSeasonRank } from '../types/metrics'

const tooltipStyle = {
  background: '#1e293b',
  border: '1px solid #334155',
  borderRadius: 8,
}

function rankWindow(history: LadderPvsSeasonRank[], endSeason: number, years: number) {
  const start = endSeason - years + 1
  return history
    .filter((r) => r.season >= start && r.season <= endSeason)
    .sort((a, b) => a.season - b.season)
}

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

  const ladderPvs = bundle.ladderPvsRanks
  const windowYears = ladderPvs?.windowYears ?? 5
  const rankHistory = rankWindow(
    ladderPvs?.byClub?.[filters.club] ?? [],
    filters.season,
    windowYears,
  )
  const currentRank = rankHistory.find((r) => r.season === filters.season)

  return (
    <>
      <PageHeader
        title={`${filters.club} — ${filters.season}`}
        subtitle="Rolling unavailable PVS, ladder vs injury rank, and wins by round."
      />
      <FilterBar />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Season unavailable PVS" value={totalUnavailable.toFixed(1)} accent="gold" />
        <StatCard
          label="Top-5 unavailable PVS"
          value={(clubRanking?.unavailableTop5 ?? 0).toFixed(1)}
          hint="Sum of highest-impact absences"
        />
        <StatCard label="Wins" value={totalWins} hint="From match results" accent="green" />
        {currentRank && (
          <StatCard
            label="Rank delta"
            value={currentRank.rankDelta > 0 ? `+${currentRank.rankDelta}` : `${currentRank.rankDelta}`}
            hint={`Ladder ${currentRank.ladderRank} vs PVS-lost ${currentRank.pvsLostRank}`}
          />
        )}
      </div>

      {rankHistory.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 mb-8">
          <h3 className="text-sm font-medium text-slate-300 mb-1">
            Ladder rank vs fewest PVS lost rank
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Last {windowYears} seasons ending {filters.season}. Rank 1 is best on each scale.
          </p>
          <div className="h-64 mb-6">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={rankHistory} margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="season" tick={{ fill: '#94a3b8' }} />
                <YAxis
                  domain={[18, 1]}
                  reversed
                  tick={{ fill: '#94a3b8' }}
                  allowDecimals={false}
                  label={{
                    value: 'Rank (1 = best)',
                    angle: -90,
                    position: 'insideLeft',
                    fill: '#64748b',
                    fontSize: 11,
                  }}
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  labelFormatter={(label) => `Season ${label}`}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="ladderRank"
                  name="Ladder rank"
                  stroke="#f5c518"
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="pvsLostRank"
                  name="PVS-lost rank"
                  stroke="#22d3ee"
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <h4 className="text-xs font-medium text-slate-400 mb-2">
            Rank delta (ladder − PVS-lost)
          </h4>
          <p className="text-xs text-slate-500 mb-3">
            Negative = finished higher on the ladder than injury toll suggests. Positive = finished
            lower.
          </p>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rankHistory} margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="season" tick={{ fill: '#94a3b8' }} />
                <YAxis tick={{ fill: '#94a3b8' }} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="rankDelta" name="Rank delta" radius={[4, 4, 0, 0]}>
                  {rankHistory.map((row) => (
                    <Cell
                      key={row.season}
                      fill={row.rankDelta < 0 ? '#22c55e' : row.rankDelta > 0 ? '#ef4444' : '#94a3b8'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          {ladderPvs?.interpretation && (
            <p className="text-xs text-slate-500 mt-4 italic">{ladderPvs.interpretation}</p>
          )}
        </div>
      )}

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
