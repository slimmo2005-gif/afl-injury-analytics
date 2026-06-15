import type { UnavailablePlayer } from '../types/metrics'

type Props = {
  club: string
  season: number
  players: UnavailablePlayer[]
  onClose: () => void
}

function formatKeyInjuries(player: UnavailablePlayer): string {
  if (player.keyInjuries?.length) return player.keyInjuries.join(' · ')
  if (player.status === 'intermittent') return 'Intermittent absence (reason not recorded)'
  return 'Not recorded — inferred from non-selection only'
}

export default function ClubKeyInjuriesModal({ club, season, players, onClose }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="key-injuries-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 px-5 py-4 border-b border-slate-800">
          <div>
            <h2 id="key-injuries-title" className="text-lg font-semibold text-slate-100">
              Key injuries
            </h2>
            <p className="text-sm text-slate-400 mt-0.5">
              {club} · {season}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 text-xl leading-none px-1"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {players.length > 0 ? (
          <ol className="divide-y divide-slate-800">
            {players.map((player, index) => (
              <li key={player.player} className="px-5 py-3">
                <div className="flex items-baseline justify-between gap-3">
                  <p className="text-sm font-medium text-slate-200">
                    <span className="text-slate-500 mr-2">{index + 1}.</span>
                    {player.player}
                  </p>
                  <p className="text-xs text-slate-500 shrink-0 tabular-nums">
                    {player.roundsMissed} injury round{player.roundsMissed === 1 ? '' : 's'}
                  </p>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {formatKeyInjuries(player)}
                </p>
                {player.unavailablePvs != null && (
                  <p className="text-[10px] text-slate-600 mt-1 tabular-nums">
                    {player.unavailablePvs.toFixed(0)} PVS lost
                  </p>
                )}
              </li>
            ))}
          </ol>
        ) : (
          <p className="px-5 py-6 text-sm text-slate-500">
            No significant injury absences recorded for this club in {season}.
          </p>
        )}

        <div className="px-5 py-3 border-t border-slate-800 text-[10px] text-slate-600 leading-relaxed">
          Ranked by injury PVS. Round counts include only injury-counted absences — weeks playing
          VFL or omitted from the AFL side without injury are excluded.
        </div>
      </div>
    </div>
  )
}
