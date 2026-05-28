import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { useMetricsContext } from '../context/MetricsContext'

export default function ModelInsights() {
  const { data } = useMetricsContext()
  const { regression } = data
  return (
    <>
      <PageHeader
        title="Model insights"
        subtitle="Explainable regression linking unavailable player value to wins and margins."
      />
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <StatCard label="Model" value={regression.model} accent="gold" />
        <StatCard label="R²" value={regression.rSquared.toFixed(2)} />
        <StatCard label="Approach" value="Interpretable" hint="No black-box ML in v1" accent="green" />
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
          <h3 className="text-sm font-medium text-slate-300 mb-3">PVS formula (planned)</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Hybrid score: performance (rolling multi-year stats, disposals, score involvements) blended with
            potential (draft pick curve). Age-weighted smoothly — e.g. 18yo ≈ 30% perf / 70% potential;
            25+ ≈ 100% performance.
          </p>
          <p className="text-sm text-slate-500 mt-4 italic">{regression.interpretation}</p>
        </div>
      </div>
    </>
  )
}
