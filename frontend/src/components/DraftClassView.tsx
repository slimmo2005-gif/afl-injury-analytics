import type { DraftClassSnapshot } from '../types/metrics'

interface DraftClassViewProps {
  draft: DraftClassSnapshot | undefined
  loading: boolean
  error: string | null
}

export default function DraftClassView({ draft, loading, error }: DraftClassViewProps) {
  if (loading) {
    return <p className="text-slate-400">Loading draft class data…</p>
  }

  if (error || !draft) {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-6 text-amber-200">
        <p className="font-medium">Draft class data unavailable</p>
      </div>
    )
  }

  const empty = draft.players.length === 0

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-[10px] uppercase tracking-widest text-emerald-400/90">Live season</p>
        <h1 className="text-2xl sm:text-3xl font-semibold text-afl-gold tracking-tight">
          {draft.draftYear} draft class — first round
        </h1>
        <p className="text-sm text-slate-400">
          {empty
            ? `First-round picks for the ${draft.draftYear} national draft are not loaded yet.`
            : `${draft.debuted} of ${draft.totalPicks} have played AFL in ${draft.season} · performance score is stats-only (no draft-potential boost)`}
        </p>
      </header>

      {empty ? (
        <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
          <p className="text-sm text-slate-400 leading-relaxed">{draft.interpretation}</p>
        </section>
      ) : (
        <>
          <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wider text-slate-500 border-b border-slate-800">
                    <th className="py-2 pr-3 font-medium">Pick</th>
                    <th className="py-2 pr-3 font-medium">Player</th>
                    <th className="py-2 pr-3 font-medium">Club</th>
                    <th className="py-2 pr-3 font-medium text-right">Games</th>
                    <th className="py-2 pr-3 font-medium text-right">Perf</th>
                    <th className="py-2 font-medium text-right">PVS</th>
                  </tr>
                </thead>
                <tbody>
                  {draft.players.map((p) => (
                    <tr
                      key={p.pick}
                      className={`border-b border-slate-800/60 ${!p.hasDebuted ? 'opacity-50' : ''}`}
                    >
                      <td className="py-2.5 pr-3 tabular-nums text-slate-400">{p.pick}</td>
                      <td className="py-2.5 pr-3 text-slate-200 font-medium">{p.player}</td>
                      <td className="py-2.5 pr-3 text-slate-400">{p.club}</td>
                      <td className="py-2.5 pr-3 text-right tabular-nums text-slate-300">
                        {p.hasDebuted ? p.games : '—'}
                      </td>
                      <td className="py-2.5 pr-3 text-right tabular-nums font-medium text-afl-gold">
                        {p.performanceScore != null ? p.performanceScore.toFixed(2) : '—'}
                      </td>
                      <td className="py-2.5 text-right tabular-nums text-slate-500">
                        {p.pvs != null ? p.pvs.toFixed(2) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-slate-600 mt-3 leading-relaxed">{draft.interpretation}</p>
          </section>

          {draft.topPerformance.length > 0 && (
            <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
              <h2 className="text-lg font-medium text-slate-200 mb-3">Top performers (stats-only)</h2>
              <ul className="space-y-2">
                {draft.topPerformance.map((p) => (
                  <li
                    key={p.pick}
                    className="flex items-center justify-between gap-3 text-sm px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-800"
                  >
                    <span className="text-slate-200">
                      #{p.pick} {p.player}{' '}
                      <span className="text-slate-500">({p.club})</span>
                    </span>
                    <span className="text-afl-gold tabular-nums font-medium">
                      {p.performanceScore != null ? p.performanceScore.toFixed(2) : '—'}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  )
}
