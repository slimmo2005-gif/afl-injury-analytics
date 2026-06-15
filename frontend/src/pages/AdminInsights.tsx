import { useMemo, useState } from 'react'
import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
import FilterBar from '../components/FilterBar'
import PageHeader from '../components/PageHeader'
import { LADDER_SIZE } from '../constants'
import { useFilters } from '../context/FilterContext'
import { useMetricsContext } from '../context/MetricsContext'
import type { LadderPvsSeasonRank } from '../types/metrics'
import {
  computeRankCorrelationR2,
  getDeltaInterpretation,
} from '../utils/clubSeasonStory'
import { formatRankDelta } from '../utils/formatRankDelta'

type InsightTab = 'luck' | 'hardest' | 'healthiest' | 'model'

interface SeasonClubRow extends LadderPvsSeasonRank {
  club: string
}

function seasonRows(
  byClub: Record<string, LadderPvsSeasonRank[]> | undefined,
  season: number,
): SeasonClubRow[] {
  if (!byClub) return []
  const rows: SeasonClubRow[] = []
  for (const [club, history] of Object.entries(byClub)) {
    const row = history.find((h) => h.season === season)
    if (row) rows.push({ club, ...row })
  }
  return rows
}

const tooltipStyle = {
  background: '#1e293b',
  border: '1px solid #334155',
  borderRadius: 8,
}

export default function AdminInsights() {
  const { data } = useMetricsContext()
  const { filters } = useFilters()
  const [tab, setTab] = useState<InsightTab>('luck')

  const byClub = data.ladderPvsRanks?.byClub
  const seasonData = useMemo(
    () => seasonRows(byClub, filters.season),
    [byClub, filters.season],
  )

  const luckLadder = useMemo(
    () => [...seasonData].sort((a, b) => a.rankDelta - b.rankDelta),
    [seasonData],
  )

  const hardestHit = useMemo(
    () => [...seasonData].sort((a, b) => b.pvsLost - a.pvsLost),
    [seasonData],
  )

  const healthiest = useMemo(
    () => [...seasonData].sort((a, b) => a.pvsLost - b.pvsLost),
    [seasonData],
  )

  const allPoints = useMemo(() => {
    if (!byClub) return []
    const pts: { club: string; season: number; pvsLostRank: number; ladderRank: number }[] = []
    for (const [club, history] of Object.entries(byClub)) {
      for (const h of history) {
        pts.push({
          club,
          season: h.season,
          pvsLostRank: h.pvsLostRank,
          ladderRank: h.ladderRank,
        })
      }
    }
    return pts
  }, [byClub])

  const r2 = useMemo(() => computeRankCorrelationR2(allPoints), [allPoints])

  const tabs: { id: InsightTab; label: string }[] = [
    { id: 'luck', label: 'Injury luck ladder' },
    { id: 'hardest', label: 'Hardest hit' },
    { id: 'healthiest', label: 'Healthiest' },
    { id: 'model', label: 'Model fit' },
  ]

  return (
    <>
      <PageHeader
        title="Injury insights"
        subtitle="League-wide views — who matched their injury profile, who didn't, and how strongly ranks align."
      />
      <FilterBar seasonOnly />
      <div className="flex flex-wrap gap-1 mb-6 border-b border-slate-800 pb-2">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 rounded-md text-sm whitespace-nowrap transition-colors ${
              tab === t.id
                ? 'bg-afl-green text-afl-gold font-medium'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'luck' && (
        <TableSection
          title={`Injury luck ladder — ${filters.season}`}
          description="Clubs ranked by rank delta (ladder rank − injury rank). Negative = outperformed injuries."
          columns={['Club', 'Ladder', 'Injury rank', 'Delta', 'Interpretation']}
          rows={luckLadder.map((r) => [
            r.club,
            String(r.ladderRank),
            String(r.pvsLostRank),
            formatRankDelta(r.rankDelta),
            getDeltaInterpretation(r.rankDelta),
          ])}
          deltaCol={3}
        />
      )}

      {tab === 'hardest' && (
        <TableSection
          title={`Hardest hit clubs — ${filters.season}`}
          description="Total PVS lost from unavailable players (higher = more impact)."
          columns={['Club', 'PVS lost', 'Injury rank', 'Ladder', 'Delta']}
          rows={hardestHit.map((r) => [
            r.club,
            r.pvsLost.toFixed(1),
            String(r.pvsLostRank),
            String(r.ladderRank),
            formatRankDelta(r.rankDelta),
          ])}
          deltaCol={4}
        />
      )}

      {tab === 'healthiest' && (
        <TableSection
          title={`Healthiest clubs — ${filters.season}`}
          description="Fewest PVS lost — injury rank 1 is the healthiest list."
          columns={['Club', 'PVS lost', 'Injury rank', 'Ladder', 'Delta']}
          rows={healthiest.map((r) => [
            r.club,
            r.pvsLost.toFixed(1),
            String(r.pvsLostRank),
            String(r.ladderRank),
            formatRankDelta(r.rankDelta),
          ])}
          deltaCol={4}
        />
      )}

      {tab === 'model' && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-1">Model fit</h3>
          <p className="text-xs text-slate-500 mb-4 max-w-2xl">
            Scatter across all clubs and seasons in the dataset. This does not prove injuries cause
            ladder position, but it shows how strongly injury impact aligns with final ladder outcomes.
            {r2 != null && (
              <span className="text-slate-400 block mt-2">
                R² ≈ {r2.toFixed(2)} (simple linear fit: injury rank vs ladder rank)
              </span>
            )}
          </p>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ left: 8, right: 16, bottom: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  type="number"
                  dataKey="pvsLostRank"
                  name="Injury rank"
                  domain={[1, LADDER_SIZE]}
                  tick={{ fill: '#94a3b8' }}
                  label={{
                    value: 'Injury-impact rank (1 = healthiest)',
                    position: 'bottom',
                    fill: '#64748b',
                    fontSize: 11,
                  }}
                />
                <YAxis
                  type="number"
                  dataKey="ladderRank"
                  name="Ladder"
                  domain={[LADDER_SIZE, 1]}
                  reversed
                  tick={{ fill: '#94a3b8' }}
                  label={{
                    value: 'Ladder position (1 = best)',
                    angle: -90,
                    position: 'insideLeft',
                    fill: '#64748b',
                    fontSize: 11,
                  }}
                />
                <ZAxis range={[40, 40]} />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(value: number, name: string) => [value, name]}
                  labelFormatter={(_, payload) => {
                    const p = payload?.[0]?.payload as { club: string; season: number } | undefined
                    return p ? `${p.club} ${p.season}` : ''
                  }}
                />
                <Scatter name="Club-season" data={allPoints} fill="#22d3ee" fillOpacity={0.7} />
                <Legend />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </>
  )
}

function TableSection({
  title,
  description,
  columns,
  rows,
  deltaCol,
}: {
  title: string
  description: string
  columns: string[]
  rows: string[][]
  deltaCol?: number
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800">
        <h3 className="text-sm font-medium text-slate-300">{title}</h3>
        <p className="text-xs text-slate-500 mt-1">{description}</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b border-slate-800">
              {columns.map((c) => (
                <th key={c} className="px-4 py-2 font-medium">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-6 text-slate-500">
                  No data for this season.
                </td>
              </tr>
            ) : (
              rows.map((row, i) => (
                <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                  {row.map((cell, j) => {
                    let className = 'px-4 py-2 text-slate-300'
                    if (j === deltaCol) {
                      const n = Number(cell.replace('+', ''))
                      if (!Number.isNaN(n)) {
                        if (n <= -2) className += ' text-emerald-400'
                        else if (n >= 2) className += ' text-orange-400'
                      }
                    }
                    if (j === 0) className += ' font-medium text-slate-100'
                    return (
                      <td key={j} className={className}>
                        {cell}
                      </td>
                    )
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
