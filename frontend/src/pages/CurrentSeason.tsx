import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
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
import ClubKeyInjuriesModal from '../components/ClubKeyInjuriesModal'
import StatCard from '../components/StatCard'
import { CURRENT_SEASON, LADDER_SIZE } from '../constants'
import { useCurrentSeason } from '../hooks/useCurrentSeason'
import { formatRankDelta } from '../utils/formatRankDelta'

const LADDER_TICKS = Array.from({ length: LADDER_SIZE }, (_, i) => i + 1)

const tooltipStyle = {
  background: '#1e293b',
  border: '1px solid #334155',
  borderRadius: 8,
}

function deltaColor(delta: number) {
  if (delta <= -2) return '#34d399'
  if (delta >= 2) return '#f87171'
  return '#94a3b8'
}

export default function CurrentSeason() {
  const { data, loading, error } = useCurrentSeason()
  const [selectedClub, setSelectedClub] = useState<string | null>(null)
  const [injuriesClub, setInjuriesClub] = useState<string | null>(null)

  const ladderChart = useMemo(() => {
    if (!data?.currentLadderPvs?.clubs) return []
    return data.currentLadderPvs.clubs.map((c) => ({
      club: c.club,
      clubShort: c.club.replace('Greater Western Sydney', 'GWS'),
      ladderRank: c.ladderRank,
      pvsLostRank: c.pvsLostRank,
      rankDelta: c.rankDelta,
      pvsLost: c.pvsLost,
      wins: c.wins,
    }))
  }, [data])

  if (loading) {
    return <p className="text-slate-400">Loading {CURRENT_SEASON} season data…</p>
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-6 text-amber-200">
        <p className="font-medium">Current season data unavailable</p>
        <p className="text-sm mt-2 text-amber-200/80">
          Run <code className="text-amber-100">python data-pipeline/scripts/update_current_season.py</code>{' '}
          to build currentSeason.json.
        </p>
        <Link to="/" className="inline-block mt-4 text-sm text-afl-gold hover:text-yellow-300">
          ← Back to 2021–2025 view
        </Link>
      </div>
    )
  }

  const round = data.meta.ladderRound ?? data.meta.round
  const defaultClub = data.defaultClub ?? data.clubs?.[0] ?? 'Collingwood'
  const activeClub = selectedClub ?? defaultClub
  const clubRoundSeries = data.clubSeries?.[activeClub] ?? data.clubUnavailableByRound

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest text-emerald-400/90 mb-1">Live season</p>
          <h1 className="text-2xl sm:text-3xl font-semibold text-afl-gold tracking-tight">
            {CURRENT_SEASON} season to date
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Through round {round} · ladder vs injury luck updated weekly
          </p>
        </div>
        <Link
          to="/"
          className="text-sm text-slate-400 hover:text-slate-200 border border-slate-700 rounded-lg px-3 py-2"
        >
          2021–2025 history →
        </Link>
      </div>

      <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 mb-8 text-sm text-slate-300">
        This page tracks the <strong className="text-slate-200">in-progress {CURRENT_SEASON} season</strong>.
        Historical analysis and the five-year injury-luck window remain on the{' '}
        <Link to="/" className="text-afl-gold hover:text-yellow-300">main club view</Link> (2021–2025).
        Correlations and regression here are indicative only — about half a season of data.
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Rounds played"
          value={String(round)}
          hint="of ~24 home-and-away"
        />
        <StatCard
          label="Hardest hit club"
          value={data.leagueOverview.topUnavailableClub}
          hint="Most PVS lost YTD"
        />
        <StatCard
          label="PVS ↔ wins (YTD)"
          value={data.leagueOverview.correlationUnavailableToWins.toFixed(2)}
          hint="In-season correlation"
        />
        <StatCard
          label="Above injury expectation"
          value={String(data.leagueOverview.clubsAboveExpectation)}
          hint="of 18 clubs"
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mb-8">
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <h2 className="text-sm font-medium text-slate-300 mb-1">
            Ladder rank vs injury-impact rank
          </h2>
          <p className="text-xs text-slate-500 mb-4">Through round {round}. Lower = better on both axes.</p>
          <ResponsiveContainer width="100%" height={360}>
            <LineChart data={ladderChart} margin={{ top: 8, right: 8, left: 0, bottom: 48 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="clubShort"
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                angle={-40}
                textAnchor="end"
                height={70}
                interval={0}
              />
              <YAxis
                domain={[1, LADDER_SIZE]}
                reversed
                ticks={LADDER_TICKS}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                width={28}
              />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend />
              <Line
                type="monotone"
                dataKey="ladderRank"
                name="Ladder"
                stroke="#fbbf24"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
              <Line
                type="monotone"
                dataKey="pvsLostRank"
                name="Injury PVS rank"
                stroke="#60a5fa"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <h2 className="text-sm font-medium text-slate-300 mb-1">Injury luck gap (rank delta)</h2>
          <p className="text-xs text-slate-500 mb-4">Ladder rank − injury rank. Negative = outperforming injuries.</p>
          <ResponsiveContainer width="100%" height={360}>
            <BarChart data={ladderChart} margin={{ top: 8, right: 8, left: 0, bottom: 48 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="clubShort"
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                angle={-40}
                textAnchor="end"
                height={70}
                interval={0}
              />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(v: number) => [formatRankDelta(v), 'Rank delta']}
              />
              <Bar dataKey="rankDelta" name="Rank delta">
                {ladderChart.map((entry) => (
                  <Cell key={entry.club} fill={deltaColor(entry.rankDelta)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 mb-8">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h2 className="text-sm font-medium text-slate-300">Weekly injury PVS — {activeClub}</h2>
          <select
            value={activeClub}
            onChange={(e) => setSelectedClub(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-md text-sm px-2 py-1 text-slate-200"
          >
            {(data.clubs ?? data.clubRankings.map((c) => c.club)).map((club) => (
              <option key={club} value={club}>
                {club}
              </option>
            ))}
          </select>
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={clubRoundSeries} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="round" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line type="monotone" dataKey="value" name="PVS lost" stroke="#f87171" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="rounded-xl border border-slate-800 overflow-hidden mb-8">
        <div className="px-4 py-3 border-b border-slate-800 bg-slate-900/60">
          <h2 className="text-sm font-medium text-slate-300">Club standings — injury PVS lost (YTD)</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-800">
                <th className="px-4 py-2 font-medium">Club</th>
                <th className="px-4 py-2 font-medium">Ladder</th>
                <th className="px-4 py-2 font-medium">Injury rank</th>
                <th className="px-4 py-2 font-medium">Delta</th>
                <th className="px-4 py-2 font-medium">PVS lost</th>
                <th className="px-4 py-2 font-medium">Wins</th>
                <th className="px-4 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {ladderChart.map((row) => (
                <tr key={row.club} className="border-b border-slate-800/80 hover:bg-slate-800/30">
                  <td className="px-4 py-2 text-slate-200">{row.clubShort}</td>
                  <td className="px-4 py-2">{row.ladderRank}</td>
                  <td className="px-4 py-2">{row.pvsLostRank}</td>
                  <td className="px-4 py-2" style={{ color: deltaColor(row.rankDelta) }}>
                    {formatRankDelta(row.rankDelta)}
                  </td>
                  <td className="px-4 py-2">{row.pvsLost.toFixed(0)}</td>
                  <td className="px-4 py-2">{row.wins}</td>
                  <td className="px-4 py-2">
                    <button
                      type="button"
                      onClick={() => setInjuriesClub(row.club)}
                      className="text-xs text-afl-gold hover:text-yellow-300"
                    >
                      Key injuries
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
        <h2 className="text-sm font-medium text-slate-300 mb-3">Most PVS lost — league (YTD)</h2>
        <div className="grid sm:grid-cols-2 gap-2">
          {data.topUnavailablePlayers.slice(0, 8).map((p) => (
            <div
              key={`${p.club}-${p.player}`}
              className="flex justify-between gap-2 text-sm px-3 py-2 rounded-lg bg-slate-800/40"
            >
              <span className="text-slate-200 truncate">
                {p.player}{' '}
                <span className="text-slate-500">({p.club})</span>
              </span>
              <span className="text-slate-400 shrink-0">{p.unavailablePvs?.toFixed(0)} PVS</span>
            </div>
          ))}
        </div>
      </div>

      {injuriesClub && data.topUnavailableByClub && (
        <ClubKeyInjuriesModal
          club={injuriesClub}
          season={CURRENT_SEASON}
          players={data.topUnavailableByClub[injuriesClub] ?? []}
          onClose={() => setInjuriesClub(null)}
        />
      )}
    </div>
  )
}
