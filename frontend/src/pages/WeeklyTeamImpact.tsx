import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CURRENT_SEASON } from '../constants'
import { useCurrentSeason } from '../hooks/useCurrentSeason'
import type { WeeklyTeamImpactClub, WeeklyTeamImpactSnapshot } from '../types/metrics'

function impactColor(pvs: number | null | undefined) {
  if (pvs == null) return 'text-slate-500'
  if (pvs <= 8) return 'text-emerald-400'
  if (pvs <= 20) return 'text-amber-300'
  return 'text-orange-400'
}

function barColor(pvs: number | null | undefined) {
  if (pvs == null) return 'bg-slate-600'
  if (pvs <= 8) return 'bg-emerald-500/70'
  if (pvs <= 20) return 'bg-amber-400/70'
  return 'bg-orange-500/70'
}

function StatusBadge({ reason }: { reason?: 'injured' | 'suspended' }) {
  if (reason === 'suspended') {
    return (
      <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-amber-300">
        suspended
      </span>
    )
  }
  return (
    <span className="rounded bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-rose-300">
      injured
    </span>
  )
}

function ClubImpactCard({ row }: { row: WeeklyTeamImpactClub }) {
  const top4 = row.missingFromOptimal.slice(0, 4)
  return (
    <article className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-100">{row.club}</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {row.teamsAnnounced
              ? `${row.selectedCount} selected · (C) best-fit ${row.cPvs ?? '—'} − (B) selected ${
                  row.selectedTeamPvs ?? '—'
                }`
              : 'Awaiting AFL team announcement'}
          </p>
        </div>
        <div className="text-right">
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Impact (C − B)</p>
          <p className={`text-2xl font-bold tabular-nums ${impactColor(row.impactPvs)}`}>
            {row.impactPvs != null ? `${row.impactPvs} PVS` : '—'}
          </p>
        </div>
      </div>

      {top4.length > 0 ? (
        <div className="mt-4">
          <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">
            Top players missing — gross vs net of replacement
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wider text-slate-500">
                  <th className="py-1.5 pr-2">Player</th>
                  <th className="py-1.5 px-2 text-right">Gross</th>
                  <th className="py-1.5 px-2">Replaced by</th>
                  <th className="py-1.5 pl-2 text-right">Net</th>
                </tr>
              </thead>
              <tbody>
                {top4.map((p) => (
                  <tr key={p.player} className="border-t border-slate-800/70">
                    <td className="py-2 pr-2">
                      <span className="text-slate-200">{p.player}</span>{' '}
                      <StatusBadge reason={p.reason} />
                      <span className="block text-[11px] text-slate-500">{p.archetypeLabel}</span>
                    </td>
                    <td className="py-2 px-2 text-right tabular-nums text-slate-300">
                      {p.grossPvs ?? p.pvs}
                    </td>
                    <td className="py-2 px-2 text-slate-400">
                      {p.replacedBy ? (
                        <>
                          <span className="truncate">{p.replacedBy}</span>
                          <span className="text-slate-600"> ({p.replacementPvs})</span>
                        </>
                      ) : (
                        <span className="text-slate-600">no cover</span>
                      )}
                    </td>
                    <td
                      className={`py-2 pl-2 text-right tabular-nums font-semibold ${impactColor(
                        p.netPvs,
                      )}`}
                    >
                      {p.netPvs ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <p className="mt-4 text-sm text-emerald-300/90">
          No best-23 players unavailable through injury or suspension.
        </p>
      )}
    </article>
  )
}

export default function WeeklyTeamImpact() {
  const { data, loading, error } = useCurrentSeason()
  const [searchParams, setSearchParams] = useSearchParams()
  const [club, setClub] = useState<string>('')

  const availableRounds = data?.weeklyTeamImpactRounds ?? []
  const currentRound = data?.weeklyTeamImpact?.round
  const roundParam = Number(searchParams.get('round'))
  const selectedRound =
    roundParam && availableRounds.includes(roundParam) ? roundParam : currentRound

  const impact: WeeklyTeamImpactSnapshot | undefined = useMemo(() => {
    if (!data || !selectedRound) return data?.weeklyTeamImpact
    if (selectedRound === data.weeklyTeamImpact?.round) return data.weeklyTeamImpact
    return data.weeklyTeamImpactByRound?.[String(selectedRound)]
  }, [data, selectedRound])

  const ladder = impact?.ladder ?? []
  const maxImpact = useMemo(
    () => ladder.reduce((m, r) => Math.max(m, r.impactPvs ?? 0), 0),
    [ladder],
  )

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
          {selectedRound !== currentRound ? ' · archived snapshot' : ''}
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
          {selectedRound === currentRound && ladder.length < 10
            ? ' Not all teams have announced line-ups yet this week.'
            : ''}
        </p>
        {availableRounds.length > 1 && (
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="text-xs text-slate-500">Prior weeks:</span>
            {[...availableRounds].reverse().map((rn) => {
              const active = rn === selectedRound
              return (
                <button
                  key={rn}
                  type="button"
                  onClick={() => {
                    setClub('')
                    if (rn === currentRound) {
                      searchParams.delete('round')
                      setSearchParams(searchParams, { replace: true })
                    } else {
                      setSearchParams({ round: String(rn) }, { replace: true })
                    }
                  }}
                  className={`rounded-lg px-2.5 py-1 text-xs border transition ${
                    active
                      ? 'border-emerald-500/50 bg-emerald-500/15 text-emerald-300'
                      : 'border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-200'
                  }`}
                >
                  Round {rn}
                  {rn === currentRound ? ' (current)' : ''}
                </button>
              )
            })}
          </div>
        )}
      </header>

      <section>
        <h2 className="text-lg font-semibold text-slate-200 mb-3">Selection impact ladder</h2>
        <p className="text-sm text-slate-500 mb-4">
          Impact = <span className="text-slate-300">(C) best-fit − (B) selected</span>: the net PVS
          a club is missing through injury or suspension, after the players who replaced them are
          counted. Lower is healthier; available players left out by selection don't count.
        </p>
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3 sm:p-4 space-y-1.5">
          {ladder.map((row) => {
            const width = maxImpact > 0 ? Math.max((row.impactPvs / maxImpact) * 100, 1.5) : 0
            return (
              <button
                key={row.club}
                type="button"
                onClick={() => setClub(row.club)}
                className={`w-full text-left rounded-lg px-2 py-2 transition hover:bg-slate-800/40 ${
                  row.club === activeClub ? 'bg-slate-800/50' : ''
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="w-7 shrink-0 text-right text-xs tabular-nums text-slate-500">
                    #{row.impactRank}
                  </span>
                  <span className="w-28 sm:w-36 shrink-0 truncate text-sm font-medium text-slate-100">
                    {row.club}
                  </span>
                  <div className="relative h-5 flex-1 rounded bg-slate-800/60">
                    <div
                      className={`absolute inset-y-0 left-0 rounded ${barColor(row.impactPvs)}`}
                      style={{ width: `${width}%` }}
                    />
                  </div>
                  <span
                    className={`w-14 shrink-0 text-right text-sm font-semibold tabular-nums ${impactColor(
                      row.impactPvs,
                    )}`}
                  >
                    {row.impactPvs ?? '—'}
                  </span>
                </div>
                <div className="mt-0.5 pl-10 text-[11px] text-slate-500">
                  (C) {row.cPvs ?? '—'} − (B) {row.selectedTeamPvs ?? '—'}
                  {' · '}
                  {row.teamStatus === 'FINAL_TEAM'
                    ? 'final team'
                    : row.teamStatus
                      ? 'provisional'
                      : row.teamsAnnounced
                        ? 'named'
                        : 'pending'}
                </div>
              </button>
            )
          })}
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
