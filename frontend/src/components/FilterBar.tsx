import { useFilters, useSeasonOptions } from '../context/FilterContext'
import { useMetricsContext } from '../context/MetricsContext'

export default function FilterBar({ seasonOnly = false }: { seasonOnly?: boolean }) {
  const { data } = useMetricsContext()
  const { filters, setSeason, setClub } = useFilters()
  const seasons = useSeasonOptions()

  const clubs =
    data.seasons?.[String(filters.season)]?.clubs ??
    data.clubs ??
    data.clubRankings.map((c) => c.club)

  return (
    <div className="flex flex-wrap gap-3 mb-6 p-3 rounded-lg bg-slate-900/50 border border-slate-800">
      {!seasonOnly && (
        <label className="flex flex-col gap-1 text-xs text-slate-500">
          Club
          <select
            value={filters.club}
            onChange={(e) => setClub(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200 min-w-[140px]"
          >
            {clubs.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="flex flex-col gap-1 text-xs text-slate-500">
        Season
        <select
          value={filters.season}
          onChange={(e) => setSeason(Number(e.target.value))}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200"
        >
          {seasons.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}
