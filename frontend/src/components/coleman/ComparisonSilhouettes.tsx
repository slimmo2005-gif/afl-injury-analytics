import { formatHeight } from '../../lib/colemanStats'

interface SilhouettePerson {
  label: string
  height_cm: number | null
  accent: string
  note?: string
}

interface ComparisonSilhouettesProps {
  people: SilhouettePerson[]
  maxHeight?: number
}

export default function ComparisonSilhouettes({
  people,
  maxHeight = 210,
}: ComparisonSilhouettesProps) {
  const minHeight = 160

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:p-6">
      <h3 className="text-sm font-medium text-slate-300 mb-1">How Nick Watson compares</h3>
      <p className="text-xs text-slate-500 mb-6">Silhouettes scaled to recorded height</p>
      <div className="flex items-end justify-center gap-4 sm:gap-8 min-h-[280px] px-2">
        {people.map((person) => {
          const h = person.height_cm
          const scale = h != null ? (h - minHeight) / (maxHeight - minHeight) : 0.15
          const barH = Math.max(48, Math.round(scale * 220))
          return (
            <div key={person.label} className="flex flex-col items-center gap-2 flex-1 max-w-[120px]">
              <div
                className="w-14 sm:w-16 rounded-t-full rounded-b-lg flex flex-col items-center justify-end overflow-hidden transition-transform hover:scale-105"
                style={{ height: barH, backgroundColor: person.accent }}
                title={h != null ? formatHeight(h) : 'Unknown'}
              >
                <div className="w-10 h-10 rounded-full mb-2 opacity-90" style={{ backgroundColor: 'rgba(255,255,255,0.15)' }} />
              </div>
              <div className="text-center">
                <p className="text-xs font-medium text-slate-200 leading-tight">{person.label}</p>
                <p className="text-xs text-slate-400 tabular-nums mt-0.5">
                  {h != null ? `${h} cm` : 'Unknown'}
                </p>
                {person.note && <p className="text-[10px] text-slate-500 mt-1">{person.note}</p>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
