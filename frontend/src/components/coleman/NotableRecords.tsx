import type { ColemanStats } from '../../types/coleman'
import { formatHeight } from '../../lib/colemanStats'

interface NotableRecordsProps {
  stats: ColemanStats
}

function RecordCard({
  label,
  value,
  detail,
}: {
  label: string
  value: string
  detail?: string
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 hover:border-slate-700 transition-colors">
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
        label="Shortest (recorded)"
        value={
          stats.shortest
            ? `${stats.shortest.player} · ${stats.shortest.height_cm} cm`
            : '—'
        }
        detail={
          stats.shortest
            ? `${stats.shortest.year} · ${stats.shortest.club}`
            : undefined
        }
      />
      <RecordCard
        label="Tallest (recorded)"
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
      />
      <RecordCard
        label="Average winner height"
        value={stats.averageHeight != null ? `${stats.averageHeight} cm` : '—'}
        detail={`Based on ${stats.withHeight} Medallists with recorded height`}
      />
      <RecordCard
        label="Under 180 cm"
        value={String(stats.under180)}
        detail="Coleman Medallists with recorded height"
      />
      <RecordCard
        label="Over 195 cm"
        value={String(stats.over195)}
        detail="Coleman Medallists with recorded height"
      />
    </div>
  )
}

export { formatHeight }
