interface StatCardProps {
  label: string
  value: string | number
  hint?: string
  accent?: 'gold' | 'green' | 'red' | 'neutral'
}

const accentMap = {
  gold: 'border-afl-gold/40 text-afl-gold',
  green: 'border-emerald-500/40 text-emerald-400',
  red: 'border-afl-red/40 text-red-400',
  neutral: 'border-slate-600 text-slate-200',
}

export default function StatCard({ label, value, hint, accent = 'neutral' }: StatCardProps) {
  return (
    <div className={`rounded-xl border bg-slate-900/60 p-4 ${accentMap[accent]}`}>
      <p className="text-xs uppercase tracking-wider text-slate-500 mb-1">{label}</p>
      <p className="text-2xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="text-xs text-slate-500 mt-2">{hint}</p>}
    </div>
  )
}
