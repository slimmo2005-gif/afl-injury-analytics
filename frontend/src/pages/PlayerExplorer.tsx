import PageHeader from '../components/PageHeader'
import { useMetricsContext } from '../context/MetricsContext'
import type { UnavailablePlayer } from '../types/metrics'

const statusColors: Record<UnavailablePlayer['status'], string> = {
  unavailable: 'bg-red-500/20 text-red-300',
  vfl_only: 'bg-amber-500/20 text-amber-300',
  intermittent: 'bg-blue-500/20 text-blue-300',
}

export default function PlayerExplorer() {
  const { data } = useMetricsContext()

  return (
    <>
      <PageHeader
        title="Player explorer"
        subtitle="Player Value Score (PVS), availability status, and participation history."
      />
      <div className="rounded-xl border border-slate-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-500 text-left">
            <tr>
              <th className="px-4 py-3 font-medium">Player</th>
              <th className="px-4 py-3 font-medium">Club</th>
              <th className="px-4 py-3 font-medium">PVS</th>
              <th className="px-4 py-3 font-medium">Rounds missed</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {data.topUnavailablePlayers.map((p) => (
              <tr key={p.player} className="border-t border-slate-800 hover:bg-slate-900/60">
                <td className="px-4 py-3 text-slate-200">{p.player}</td>
                <td className="px-4 py-3 text-slate-400">{p.club}</td>
                <td className="px-4 py-3 tabular-nums text-afl-gold">{p.pvs.toFixed(1)}</td>
                <td className="px-4 py-3 tabular-nums">{p.roundsMissed}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded ${statusColors[p.status]}`}>
                    {p.status.replace('_', ' ')}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-600 mt-4">
        Availability inferred from AFL participation — not official injury lists (Phase 1).
      </p>
    </>
  )
}
