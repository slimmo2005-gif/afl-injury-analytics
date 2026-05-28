const clubs = ['Collingwood', 'Brisbane', 'Carlton', 'Geelong', 'Gold Coast', 'Western Bulldogs']
const seasons = [2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014, 2013, 2012]

export default function FilterBar() {
  return (
    <div className="flex flex-wrap gap-3 mb-6 p-3 rounded-lg bg-slate-900/50 border border-slate-800">
      <label className="flex flex-col gap-1 text-xs text-slate-500">
        Club
        <select className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200 min-w-[140px]">
          {clubs.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs text-slate-500">
        Season
        <select className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200">
          {seasons.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs text-slate-500">
        Round
        <select className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200">
          {Array.from({ length: 24 }, (_, i) => (
            <option key={i + 1}>{i + 1}</option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs text-slate-500">
        Age cohort
        <select className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200">
          <option>All</option>
          <option>Under 22</option>
          <option>22–27</option>
          <option>28+</option>
        </select>
      </label>
      <p className="self-end text-xs text-slate-600 ml-auto">Filters wireframed — not wired yet</p>
    </div>
  )
}
