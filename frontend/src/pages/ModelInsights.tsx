import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { useSeasonData } from '../hooks/useSeasonData'

export default function ModelInsights() {
  const data = useSeasonData()
  const { regression } = data
  return (
    <>
      <PageHeader
        title="Model insights"
        subtitle="Explainable regression linking unavailable player value to wins and margins."
      />
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <StatCard label="Model" value={regression.model} accent="gold" />
        <StatCard label="Wins R²" value={regression.rSquared.toFixed(2)} />
        <StatCard
          label="Margin R²"
          value={(regression.marginRSquared ?? 0).toFixed(2)}
          hint="Unavailable PVS vs avg margin"
          accent="green"
        />
      </div>
      <div className="grid md:grid-cols-2 gap-6">
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Coefficients (sample)</h3>
          <dl className="space-y-2 text-sm">
            {Object.entries(regression.coefficients).map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-slate-800 py-2">
                <dt className="text-slate-400 font-mono">{k}</dt>
                <dd className="text-afl-gold tabular-nums">{v.toFixed(2)}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-3">PVS formula</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            PVS = w(age) × performance + (1 − w(age)) × potential. Performance uses rolling z-scored
            disposals, goals, and score involvements. Potential follows an exponential draft-pick curve
            (pick 1 ≈ 9.5, pick 50 ≈ 2). At age 18, w ≈ 30%; at 25+, w = 100%.
          </p>
          <p className="text-sm text-slate-500 mt-4 italic">{regression.interpretation}</p>
        </div>
      </div>
    </>
  )
}
