import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CURRENT_SEASON } from '../constants'
import { useCurrentSeason } from '../hooks/useCurrentSeason'
import type { WeeklyTeamImpactClub } from '../types/metrics'

function impactColor(pvs: number | null | undefined) {
  if (pvs == null) return 'text-slate-500'
  if (pvs <= 8) return 'text-emerald-400'
  if (pvs <= 20) return 'text-amber-300'
  return 'text-orange-400'
}

function ClubImpactCard({ row }: { row: WeeklyTeamImpactClub }) {
  return (
    <article className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-100">{row.club}</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {row.teamsAnnounced
              ? `${row.selectedCount} selected · optimal gap ${row.pvsGap ?? '—'} PVS`
              : 'Awaiting AFL team announcement'}
          </p>
        </div>
        <div className="text-right">
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Selection impact</p>
          <p className={`text-2xl font-bold tabular-nums ${impactColor(row.impactPvs)}`}>
            {row.impactPvs != null ? `${row.impactPvs} PVS` : '—'}
          </p>
        </div>
      </div>

      {row.missingFromOptimal.length > 0 && (
        <div className="mt-4">
          <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">
            Best-23 players not named this week
          </p>
          <ul className="space-y-1.5">
            {row.missingFromOptimal.slice(0, 8).map((p) => (
              <li
                key={p.player}
                className="flex items-center justify-between gap-2 text-sm px-2 py-1.5 rounded-lg bg-slate-800/40"
              >
                <span className="text-slate-200 truncate">
                  {p.player}
                  {p.injured && (
                    <span className="ml-2 rounded bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-rose-300">
                      injured
                    </span>
                  )}
                  <span className="text-slate-500 text-xs ml-2">{p.archetypeLabel}</span>
                </span>
                <span className="text-slate-300 tabular-nums shrink-0">{p.pvs} PVS</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  )
}

export default function WeeklyTeamImpact() {
  const { data, loading, error } = useCurrentSeason()
  const [club, setClub] = useState<string>('')

  const impact = data?.weeklyTeamImpact
  const ladder = impact?.ladder ?? []

  const activeClub = useMemo(() => {
    if (!ladder.length) return null
    if (club && ladder.some((r) => r.club === club)) return club
    return ladder[0].club
  }, [club, ladder])

  const activeRow = activeClub ? impact?.byClub[activeClub] : null

  if (loading) {
    return <p className="text-slate-400">Loading weekly team impact…</p>
  }
  if (error || !data) {
    return <p className="text-red-400">Could not load current season data.</p>
  }
  if (!impact) {
    return (
      <p className="text-slate-400">
        Weekly team impact data is not available yet. Run the current-season export after team
        announcements.
      </p>
    )
  }

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-xs uppercase tracking-[0.2em] text-afl-gold">Weekly selection impact</p>
        <h1 className="text-2xl sm:text-3xl font-semibold text-slate-100">
          Injury impact vs optimal team
        </h1>
        <p className="text-sm text-slate-400 max-w-3xl leading-relaxed">{impact.interpretation}</p>
        <p className="text-xs text-slate-500">
          Round {impact.round} · {CURRENT_SEASON} season · line-ups from{' '}
          <a
            href="https://www.afl.com.au/matches/team-lineups"
            target="_blank"
            rel="noreferrer"
            className="text-emerald-300 hover:text-emerald-200 underline"
          >
            AFL.com Team Line-ups
          </a>
          {impact.teamsFinal === false ? ' (provisional teams)' : ' (final teams)'}
          {impact.lastUpdated
            ? ` · updated ${new Date(impact.lastUpdated).toLocaleString('en-AU', {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
              })}`
            : ''}
          . Teams on a bye are excluded.
        </p>
        <Link to="/current" className="text-xs text-emerald-300 hover:text-emerald-200">
          ← Back to {CURRENT_SEASON} injury overview
        </Link>
      </header>

      <section>
        <h2 className="text-lg font-semibold text-slate-200 mb-3">Selection impact ladder</h2>
        <p className="text-sm text-slate-500 mb-4">
          Lower impact = selected side is closer to the optimal 23 (healthier selection).
        </p>
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">
                <th className="px-4 py-3">Rank</th>
                <th className="px-4 py-3">Club</th>
                <th className="px-4 py-3 text-right">Impact PVS</th>
                <th className="px-4 py-3 text-right hidden sm:table-cell">Optimal</th>
                <th className="px-4 py-3 text-right hidden sm:table-cell">Selected</th>
                <th className="px-4 py-3 hidden md:table-cell">Status</th>
              </tr>
            </thead>
            <tbody>
              {ladder.map((row) => (
                <tr
                  key={row.club}
                  className={`border-b border-slate-800/80 cursor-pointer transition hover:bg-slate-800/30 ${
                    row.club === activeClub ? 'bg-slate-800/40' : ''
                  }`}
                  onClick={() => setClub(row.club)}
                >
                  <td className="px-4 py-3 tabular-nums text-slate-400">#{row.impactRank}</td>
                  <td className="px-4 py-3 font-medium text-slate-100">{row.club}</td>
                  <td className={`px-4 py-3 text-right tabular-nums font-semibold ${impactColor(row.impactPvs)}`}>
                    {row.impactPvs ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-400 hidden sm:table-cell">
                    {row.bestTeamPvs}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-400 hidden sm:table-cell">
                    {row.selectedTeamPvs ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500 hidden md:table-cell">
                    {row.teamStatus === 'FINAL_TEAM'
                      ? 'Final team'
                      : row.teamStatus
                        ? 'Provisional'
                        : row.teamsAnnounced
                          ? 'Named'
                          : 'Pending'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {impact.matchups.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-slate-200 mb-3">Round {impact.round} match-ups</h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {impact.matchups.map((m) => (
              <article
                key={`${m.home}-${m.away}`}
                className="rounded-xl border border-slate-800 bg-slate-900/40 p-4"
              >
                <p className="text-base font-semibold text-slate-100">
                  {m.home} <span className="text-slate-500 font-normal">vs</span> {m.away}
                </p>
                <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-[10px] uppercase text-slate-500">{m.home}</p>
                    <p className={`font-semibold tabular-nums ${impactColor(m.homeImpactPvs)}`}>
                      {m.homeImpactPvs} PVS
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase text-slate-500">{m.away}</p>
                    <p className={`font-semibold tabular-nums ${impactColor(m.awayImpactPvs)}`}>
                      {m.awayImpactPvs} PVS
                    </p>
                  </div>
                </div>
                <p className="mt-3 text-xs text-slate-400 leading-snug">{m.interpretation}</p>
              </article>
            ))}
          </div>
        </section>
      )}

      {activeRow && (
        <section>
          <h2 className="text-lg font-semibold text-slate-200 mb-3">{activeRow.club} detail</h2>
          <ClubImpactCard row={activeRow} />
        </section>
      )}
    </div>
  )
}
