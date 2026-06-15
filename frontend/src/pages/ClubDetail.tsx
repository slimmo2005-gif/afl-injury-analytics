import { useMemo, useState } from 'react'
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
import StatCard from '../components/StatCard'
import { LADDER_SIZE } from '../constants'
import { useFilters } from '../context/FilterContext'
import { useSeasonData } from '../hooks/useSeasonData'
import { useMetricsContext } from '../context/MetricsContext'
import type { LadderPvsSeasonRank } from '../types/metrics'
import {
  buildClubSeasonStoryData,
  chartTooltipNarrative,
  generateClubSeasonSummary,
  generateHeadline,
  generateShareHeadlines,
  generateSubheadline,
  getMetricCardContent,
  type StoryAccent,
} from '../utils/clubSeasonStory'
import { formatRankDelta, RANK_DELTA_DOMAIN } from '../utils/formatRankDelta'

const LADDER_TICKS = Array.from({ length: LADDER_SIZE }, (_, i) => i + 1)

function rankWindow(history: LadderPvsSeasonRank[], endSeason: number, years: number) {
  const start = endSeason - years + 1
  return history
    .filter((r) => r.season >= start && r.season <= endSeason)
    .sort((a, b) => a.season - b.season)
}

const tooltipStyle = {
  background: '#1e293b',
  border: '1px solid #334155',
  borderRadius: 8,
}

const accentToStat: Record<StoryAccent, 'green' | 'orange' | 'neutral'> = {
  positive: 'green',
  warning: 'orange',
  neutral: 'neutral',
}

function HowToReadPanel() {
  const [open, setOpen] = useState(true)
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 mb-8 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-800/30 transition-colors"
      >
        <span className="text-sm font-medium text-slate-300">How to read this</span>
        <span className="text-slate-500 text-xs">{open ? 'Hide' : 'Show'}</span>
      </button>
      {open && (
        <div className="px-4 pb-4 text-sm text-slate-400 space-y-3 border-t border-slate-800/80 pt-3">
          <p>
            <strong className="text-slate-300 font-medium">PVS</strong> stands for Player Value Score.
            It gives more weight to important players than fringe players. A club losing a best-22
            midfielder for 10 weeks hurts more than losing a depth player for 2 weeks. PVS lost
            estimates how much player value each club was missing during the season.
          </p>
          <p>
            <strong className="text-slate-300 font-medium">Injury-impact rank</strong> compares clubs
            by unavailability. Rank 1 means the healthiest list (fewest PVS lost). Rank 18 means the
            hardest hit.
          </p>
          <p>
            <strong className="text-slate-300 font-medium">Rank delta</strong> compares ladder rank to
            injury rank. Negative means the club outperformed its injury profile. Positive means it
            underperformed.
          </p>
        </div>
      )}
    </div>
  )
}

export default function ClubDetail() {
  const data = useSeasonData()
  const { filters } = useFilters()
  const { data: bundle } = useMetricsContext()

  const seasonKey = String(filters.season)
  const rounds =
    bundle.seasons?.[seasonKey]?.clubSeries?.[filters.club] ?? data.clubUnavailableByRound

  const clubRanking = data.clubRankings.find((c) => c.club === filters.club)
  const totalUnavailable = rounds.reduce((s, r) => s + r.value, 0)
  const top5 = clubRanking?.unavailableTop5 ?? 0

  const ladderPvs = bundle.ladderPvsRanks
  const windowYears = ladderPvs?.windowYears ?? 5
  const fullHistory = ladderPvs?.byClub?.[filters.club] ?? []
  const rankHistory = rankWindow(fullHistory, filters.season, windowYears)
  const currentRank = rankHistory.find((r) => r.season === filters.season)

  const storyData = useMemo(() => {
    if (!currentRank) return null
    return buildClubSeasonStoryData(
      filters.club,
      filters.season,
      currentRank,
      totalUnavailable,
      top5,
    )
  }, [currentRank, filters.club, filters.season, totalUnavailable, top5])

  const headline = storyData ? generateHeadline(storyData) : null
  const subheadline = storyData ? generateSubheadline(storyData, fullHistory) : null
  const summary = storyData ? generateClubSeasonSummary(storyData) : null
  const shareHeadlines = storyData ? generateShareHeadlines(storyData) : []
  const metricCards = storyData ? getMetricCardContent(storyData) : []

  const deltaAccent = storyData
    ? storyData.rankDelta <= -2
      ? 'text-emerald-400'
      : storyData.rankDelta >= 2
        ? 'text-orange-400'
        : 'text-slate-200'
    : 'text-slate-200'

  return (
    <>
      <FilterBar />

      {storyData && headline && (
        <section className="mb-8 rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/80 to-slate-950 p-6 sm:p-8">
          <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-3">
            {filters.club} · {filters.season}
          </p>
          <h2 className={`text-2xl sm:text-3xl lg:text-4xl font-bold leading-tight ${deltaAccent}`}>
            {headline}
          </h2>
          {subheadline && (
            <p className="text-base text-slate-400 mt-3">{subheadline}</p>
          )}
          {summary && (
            <p className="text-sm text-slate-400 mt-4 max-w-3xl leading-relaxed">{summary}</p>
          )}
        </section>
      )}

      {!storyData && (
        <section className="mb-8 rounded-xl border border-slate-800 bg-slate-900/40 p-6">
          <h2 className="text-xl font-semibold text-slate-200">
            {filters.club} — {filters.season}
          </h2>
          <p className="text-sm text-slate-500 mt-2">
            Ladder vs injury rank data is not available for this club/season yet.
          </p>
        </section>
      )}

      <HowToReadPanel />

      {metricCards.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {metricCards.map((card) => (
            <StatCard
              key={card.title}
              label={card.title}
              value={card.mainValue}
              hint={card.subtitle}
              accent={accentToStat[card.accent]}
            />
          ))}
        </div>
      )}

      {rankHistory.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 mb-8">
          <h3 className="text-lg font-medium text-slate-200 mb-1">
            Did ladder position follow injury luck?
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Lower numbers are better. If the lines move together, injuries may explain part of the
            season. Last {windowYears} seasons ending {filters.season}.
          </p>
          <div className="h-72 mb-6">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={rankHistory} margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="season" tick={{ fill: '#94a3b8' }} />
                <YAxis
                  domain={[LADDER_SIZE, 1]}
                  reversed
                  ticks={LADDER_TICKS}
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
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null
                    const row = payload[0]?.payload as LadderPvsSeasonRank
                    return (
                      <div style={tooltipStyle} className="p-3 text-xs max-w-xs">
                        <p className="text-slate-300 font-medium mb-2">Season {label}</p>
                        <p className="text-slate-400 mb-2">
                          {chartTooltipNarrative(
                            filters.club,
                            row.ladderRank,
                            row.pvsLostRank,
                            row.rankDelta,
                          )}
                        </p>
                        <p className="text-slate-500">
                          Ladder #{row.ladderRank} · Injury #{row.pvsLostRank}
                        </p>
                      </div>
                    )
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="ladderRank"
                  name="Ladder position"
                  stroke="#f5c518"
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="pvsLostRank"
                  name="Injury-impact rank"
                  stroke="#22d3ee"
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <h4 className="text-xs font-medium text-slate-400 mb-2">Rank delta by season</h4>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rankHistory} margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="season" tick={{ fill: '#94a3b8' }} />
                <YAxis
                  domain={RANK_DELTA_DOMAIN}
                  ticks={[-15, -10, -5, 0, 5, 10, 15]}
                  tick={{ fill: '#94a3b8' }}
                  allowDecimals={false}
                  tickFormatter={formatRankDelta}
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(value: number) => [
                    `${formatRankDelta(value)} (ladder − injury rank)`,
                    'Delta',
                  ]}
                />
                <Bar dataKey="rankDelta" name="Rank delta" radius={[4, 4, 0, 0]}>
                  {rankHistory.map((row) => (
                    <Cell
                      key={row.season}
                      fill={
                        row.rankDelta < 0
                          ? '#22c55e'
                          : row.rankDelta > 0
                            ? '#f97316'
                            : '#94a3b8'
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {shareHeadlines.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 mb-8">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Share this insight</h3>
          <ul className="space-y-2">
            {shareHeadlines.map((h, i) => (
              <li
                key={i}
                className="text-sm text-slate-400 pl-3 border-l-2 border-afl-gold/40 py-1"
              >
                {h}
              </li>
            ))}
          </ul>
        </div>
      )}

      <details className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <summary className="text-sm font-medium text-slate-400 cursor-pointer hover:text-slate-300">
          Unavailable PVS & wins by round (detail)
        </summary>
        <div className="h-72 mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rounds}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="round" tick={{ fill: '#94a3b8' }} />
              <YAxis yAxisId="left" tick={{ fill: '#94a3b8' }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: '#94a3b8' }} domain={[0, 1]} />
              <Tooltip contentStyle={tooltipStyle} />
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
      </details>
    </>
  )
}
