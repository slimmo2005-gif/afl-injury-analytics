import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import ClubKeyInjuriesModal from '../components/ClubKeyInjuriesModal'
import { CURRENT_SEASON } from '../constants'
import { useCurrentSeason } from '../hooks/useCurrentSeason'
import type { UnavailablePlayer } from '../types/metrics'
import { formatRankDelta } from '../utils/formatRankDelta'

function deltaColor(delta: number) {
  if (delta <= -2) return 'text-emerald-400'
  if (delta >= 2) return 'text-orange-400'
  return 'text-slate-200'
}

function RankBlock({
  label,
  rank,
  accent,
}: {
  label: string
  rank: number
  accent: 'gold' | 'blue'
}) {
  const ring = accent === 'gold' ? 'border-afl-gold/50 text-afl-gold' : 'border-sky-500/50 text-sky-300'
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-[10px] uppercase tracking-widest text-slate-500">{label}</span>
      <div
        className={`flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 rounded-2xl border-2 bg-slate-900/80 text-3xl sm:text-4xl font-bold tabular-nums ${ring}`}
      >
        {rank}
      </div>
    </div>
  )
}

function TopFiveList({
  players,
  onMore,
}: {
  players: UnavailablePlayer[]
  onMore?: () => void
}) {
  if (!players.length) {
    return <p className="text-sm text-slate-500">No injury-counted absences recorded yet.</p>
  }
  return (
    <ul className="space-y-2">
      {players.slice(0, 5).map((p, i) => (
        <li
          key={`${p.player}-${i}`}
          className="flex items-center justify-between gap-3 text-sm px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-800"
        >
          <div className="min-w-0">
            <span className="text-slate-200 font-medium truncate block">{p.player}</span>
            <span className="text-xs text-slate-500">
              {p.roundsMissed} injury round{p.roundsMissed === 1 ? '' : 's'}
              {p.keyInjuries?.length ? ` · ${p.keyInjuries.join(', ')}` : ''}
            </span>
          </div>
          <span className="text-slate-300 tabular-nums shrink-0 font-medium">
            {(p.unavailablePvs ?? 0).toFixed(0)} PVS
          </span>
        </li>
      ))}
      {onMore && players.length > 0 && (
        <button
          type="button"
          onClick={onMore}
          className="text-xs text-afl-gold hover:text-yellow-300 mt-1"
        >
          Full injury detail →
        </button>
      )}
    </ul>
  )
}

export default function CurrentSeason() {
  const { data, loading, error } = useCurrentSeason()
  const [club, setClub] = useState('Collingwood')
  const [injuriesOpen, setInjuriesOpen] = useState(false)

  const clubs = useMemo(() => {
    if (!data?.currentLadderPvs?.clubs) return []
    return [...data.currentLadderPvs.clubs].sort((a, b) => a.ladderRank - b.ladderRank)
  }, [data])

  const clubNames = useMemo(() => clubs.map((c) => c.club), [clubs])

  const active = useMemo(() => clubs.find((c) => c.club === club) ?? clubs[0], [clubs, club])

  const topFive = useMemo(() => {
    if (!data?.topUnavailableByClub || !active) return []
    return data.topUnavailableByClub[active.club] ?? []
  }, [data, active])

  if (loading) {
    return <p className="text-slate-400">Loading {CURRENT_SEASON} season data…</p>
  }

  if (error || !data || !active) {
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

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest text-emerald-400/90 mb-1">Live season</p>
          <h1 className="text-2xl sm:text-3xl font-semibold text-afl-gold tracking-tight">
            {CURRENT_SEASON} — club view
          </h1>
          <p className="text-sm text-slate-400 mt-1">Through round {round} · ladder vs injury luck</p>
        </div>
        <Link
          to="/"
          className="text-sm text-slate-400 hover:text-slate-200 border border-slate-700 rounded-lg px-3 py-2"
        >
          2021–2025 history →
        </Link>
      </div>

      <div className="flex flex-wrap gap-3 mb-6 p-3 rounded-lg bg-slate-900/50 border border-slate-800">
        <label className="flex flex-col gap-1 text-xs text-slate-500">
          Club
          <select
            value={active.club}
            onChange={(e) => setClub(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200 min-w-[160px]"
          >
            {clubNames.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      </div>

      <section className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/80 to-slate-950 p-6 sm:p-8 mb-8">
        <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-4">
          {active.club} · {CURRENT_SEASON} YTD
        </p>

        <div className="grid lg:grid-cols-2 gap-8 items-start">
          <div>
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-6 sm:gap-10 mb-6">
              <RankBlock label="Ladder" rank={active.ladderRank} accent="gold" />
              <div className="flex flex-col items-center gap-1 px-2">
                <span className="text-[10px] uppercase tracking-widest text-slate-600">vs</span>
                <span className={`text-2xl font-bold tabular-nums ${deltaColor(active.rankDelta)}`}>
                  {formatRankDelta(active.rankDelta)}
                </span>
                <span className="text-[10px] text-slate-500 text-center max-w-[5rem]">rank delta</span>
              </div>
              <RankBlock label="Injury luck" rank={active.pvsLostRank} accent="blue" />
            </div>

            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
              <div>
                <dt className="text-slate-500 text-xs">Wins</dt>
                <dd className="text-slate-100 font-semibold text-lg tabular-nums">{active.wins}</dd>
              </div>
              <div>
                <dt className="text-slate-500 text-xs">PVS lost</dt>
                <dd className="text-slate-100 font-semibold text-lg tabular-nums">
                  {active.pvsLost.toFixed(0)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500 text-xs">Percentage</dt>
                <dd className="text-slate-100 font-semibold text-lg tabular-nums">
                  {active.percentage.toFixed(1)}%
                </dd>
              </div>
            </dl>

            <p className="text-sm text-slate-400 mt-4 leading-relaxed">
              {active.rankDelta < 0 ? (
                <>
                  <span className={deltaColor(active.rankDelta)}>Outperforming</span> injury luck — sitting{' '}
                  {Math.abs(active.rankDelta)} place{Math.abs(active.rankDelta) === 1 ? '' : 's'} higher on the
                  ladder than the injury toll suggests.
                </>
              ) : active.rankDelta > 0 ? (
                <>
                  <span className={deltaColor(active.rankDelta)}>Underperforming</span> injury luck —{' '}
                  {active.rankDelta} place{active.rankDelta === 1 ? '' : 's'} lower on the ladder than the injury
                  toll suggests.
                </>
              ) : (
                <>Ladder position matches the injury-impact rank.</>
              )}
            </p>
          </div>

          <div>
            <h2 className="text-sm font-medium text-slate-300 mb-3">Top 5 — PVS lost to injury</h2>
            <TopFiveList players={topFive} onMore={() => setInjuriesOpen(true)} />
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-sm font-medium text-slate-400 mb-3">All clubs — quick jump</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {clubs.map((c) => {
            const players = data.topUnavailableByClub?.[c.club] ?? []
            const top = players[0]
            const selected = c.club === active.club
            return (
              <button
                key={c.club}
                type="button"
                onClick={() => setClub(c.club)}
                className={`text-left rounded-xl border p-4 transition-colors ${
                  selected
                    ? 'border-emerald-500/40 bg-emerald-500/10'
                    : 'border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/60'
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="font-medium text-slate-200 text-sm truncate">{c.club}</span>
                  <span className={`text-xs font-medium tabular-nums shrink-0 ${deltaColor(c.rankDelta)}`}>
                    {formatRankDelta(c.rankDelta)}
                  </span>
                </div>
                <div className="flex gap-4 text-xs text-slate-500 mb-2">
                  <span>
                    Ladder <strong className="text-afl-gold">{c.ladderRank}</strong>
                  </span>
                  <span>
                    Injury <strong className="text-sky-300">{c.pvsLostRank}</strong>
                  </span>
                  <span>{c.wins}W</span>
                </div>
                {top ? (
                  <p className="text-xs text-slate-500 truncate">
                    Top miss: {top.player} ({(top.unavailablePvs ?? 0).toFixed(0)} PVS)
                  </p>
                ) : (
                  <p className="text-xs text-slate-600">No injury absences</p>
                )}
              </button>
            )
          })}
        </div>
      </section>

      {injuriesOpen && (
        <ClubKeyInjuriesModal
          club={active.club}
          season={CURRENT_SEASON}
          players={topFive}
          onClose={() => setInjuriesOpen(false)}
        />
      )}
    </div>
  )
}
