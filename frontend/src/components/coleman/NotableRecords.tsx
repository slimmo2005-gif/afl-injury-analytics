import type { ColemanStats } from '../../types/coleman'
import { formatHeight } from '../../lib/colemanStats'

interface NotableRecordsProps {
  stats: ColemanStats
}

function RecordCard({
  label,
  value,
  detail,
  accent,
}: {
  label: string
  value: string
  detail?: string
  accent?: 'gold' | 'amber'
}) {
  const border =
    accent === 'gold'
      ? 'border-afl-gold/30'
      : accent === 'amber'
        ? 'border-amber-700/30'
        : 'border-slate-800'
  return (
    <div className={`rounded-xl border bg-slate-900/50 p-4 hover:border-slate-700 transition-colors ${border}`}>
      <p className="text-xs uppercase tracking-wider text-slate-500">{label}</p>
      <p className="text-lg sm:text-xl font-semibold text-slate-100 mt-1 leading-snug">{value}</p>
      {detail && <p className="text-xs text-slate-500 mt-2">{detail}</p>}
    </div>
  )
}

export default function NotableRecords({ stats }: NotableRecordsProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      <RecordCard
        label="Shortest Coleman Medallist"
        value={
          stats.shortestColemanMedallist
            ? `${stats.shortestColemanMedallist.player} · ${stats.shortestColemanMedallist.height_cm} cm`
            : '—'
        }
        detail={
          stats.shortestColemanMedallist
            ? `${stats.shortestColemanMedallist.year} · ${stats.shortestColemanMedallist.club}. Coleman Medal first presented 1981; 1955+ recognised retrospectively in 2001.`
            : undefined
        }
        accent="gold"
      />
      <RecordCard
        label="Shortest Leading Goalkicker Medallist"
        value={
          stats.shortestLeadingGoalkickerMedallist
            ? `${stats.shortestLeadingGoalkickerMedallist.player} · ${stats.shortestLeadingGoalkickerMedallist.height_cm} cm`
            : '—'
        }
        detail={
          stats.shortestLeadingGoalkickerMedallist
            ? `${stats.shortestLeadingGoalkickerMedallist.year} · ${stats.shortestLeadingGoalkickerMedallist.club}. Separate medal for 1897–1954 league leaders — not a Coleman Medal.`
            : '1897–1954 league leaders (distinct from Coleman Medal)'
        }
        accent="amber"
      />
      <RecordCard
        label="Tallest Coleman Medallist"
        value={
          stats.tallest
            ? `${stats.tallest.player} · ${stats.tallest.height_cm} cm`
            : '—'
        }
        detail={
          stats.tallest
            ? `${stats.tallest.year} · ${stats.tallest.club}`
            : undefined
        }
      />
      <RecordCard
        label="Most common height band"
        value={stats.mostCommonBand}
        detail="Among Coleman Medallists with recorded height"
      />
      <RecordCard
        label="Average Coleman Medallist height"
        value={stats.averageHeight != null ? `${stats.averageHeight} cm` : '—'}
        detail={`Based on ${stats.withHeight} Coleman Medallists with recorded height`}
      />
      <RecordCard
        label="Under 180 cm (Coleman Medallists)"
        value={String(stats.under180)}
        detail="Includes retrospective winners from 1955"
      />
      <RecordCard
        label="Over 195 cm (Coleman Medallists)"
        value={String(stats.over195)}
        detail="Includes retrospective winners from 1955"
      />
    </div>
  )
}

export { formatHeight }
