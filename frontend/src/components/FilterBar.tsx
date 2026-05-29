import { useFilters } from '../context/FilterContext'
import { useMetricsContext } from '../context/MetricsContext'

export default function FilterBar() {
  const { data } = useMetricsContext()
  const { filters, setSeason, setClub, setAgeCohort } = useFilters()

  const seasons = data.meta.seasons ?? [data.meta.season]
  const clubs =
    data.seasons?.[String(filters.season)]?.clubs ??
    data.clubs ??
    data.clubRankings.map((c) => c.club)

  return (
    <div className="flex flex-wrap gap-3 mb-6 p-3 rounded-lg bg-slate-900/50 border border-slate-800">
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
      <label className="flex flex-col gap-1 text-xs text-slate-500">
        Season
        <select
          value={filters.season}
          onChange={(e) => setSeason(Number(e.target.value))}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200"
        >
          {[...seasons].sort((a, b) => b - a).map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs text-slate-500">
        Age cohort
        <select
          value={filters.ageCohort}
          onChange={(e) => setAgeCohort(e.target.value as typeof filters.ageCohort)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200"
        >
          <option value="all">All</option>
          <option value="u22">Under 22</option>
          <option value="22-27">22–27</option>
          <option value="28+">28+</option>
        </select>
      </label>
      <p className="self-end text-xs text-slate-500 ml-auto">
        Phase 2 · PVS-weighted filters
      </p>
    </div>
  )
}
