import type { ReactNode } from 'react'
import {
  computeSeasonLeagueHighlights,
  formatOverachieverPlaces,
} from '../utils/seasonLeagueHighlights'
import type { LadderPvsSeasonRank } from '../types/metrics'

interface LeagueSeasonSummaryProps {
  season: number
  byClub: Record<string, LadderPvsSeasonRank[]> | undefined
}

function HighlightRow({
  icon,
  label,
  children,
}: {
  icon: string
  label: string
  children: ReactNode
}) {
  return (
    <div className="flex gap-3 items-start">
      <span className="text-lg leading-none mt-0.5 shrink-0" aria-hidden>
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-widest text-slate-500">{label}</p>
        <p className="text-sm font-medium text-slate-200 mt-0.5">{children}</p>
      </div>
    </div>
  )
}

export default function LeagueSeasonSummary({ season, byClub }: LeagueSeasonSummaryProps) {
  const highlights = computeSeasonLeagueHighlights(season, byClub)
  const { biggestOverachiever, hardestHit, luckiestClub } = highlights
  const hasAny = biggestOverachiever || hardestHit || luckiestClub

  return (
    <aside className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 h-full flex flex-col">
      <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-4">
        {season} at a glance
      </p>

      {hasAny ? (
        <div className="space-y-4 flex-1">
          {biggestOverachiever && (
            <HighlightRow icon="🏆" label="Biggest overachiever">
              {biggestOverachiever.club}{' '}
              <span className="text-emerald-400 font-normal">
                ({formatOverachieverPlaces(biggestOverachiever.rankDelta)})
              </span>
            </HighlightRow>
          )}
          {hardestHit && (
            <HighlightRow icon="🏥" label="Hardest hit">
              {hardestHit.club}
            </HighlightRow>
          )}
          {luckiestClub && (
            <HighlightRow icon="🍀" label="Luckiest club">
              {luckiestClub.club}
            </HighlightRow>
          )}
        </div>
      ) : (
        <p className="text-sm text-slate-500 flex-1">
          League highlights are not available for {season} yet.
        </p>
      )}

      <p className="text-[10px] text-slate-600 mt-4 pt-3 border-t border-slate-800/80">
        One glance — injury luck vs ladder finish across the AFL.
      </p>
    </aside>
  )
}
