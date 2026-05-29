import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { useMetricsContext } from '../context/MetricsContext'
import { useFilters } from '../context/FilterContext'
import { useSeasonData } from '../hooks/useSeasonData'

export default function SeasonExplorer() {
  const { source } = useMetricsContext()
  const data = useSeasonData()
  const { filters } = useFilters()
  return (
    <>
      <PageHeader
        title="Season explorer"
        subtitle="Compare ladder position, percentage, and injury-adjusted expectations across seasons (2012+)."
      />
      <div className="grid md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <StatCard label="Selected season" value={filters.season} accent="gold" />
          <StatCard
            label="Data source"
            value={source === 'live' ? (data.meta.dataSource ?? 'ETL') : 'Mock'}
            hint={data.meta.generatedAt?.slice(0, 10)}
          />
          <div className="rounded-xl border border-dashed border-slate-700 p-8 text-center text-slate-500 text-sm">
            Ladder-adjusted chart · win % vs unavailable value · rolling form
            <br />
            <span className="text-xs mt-2 block">Populated after Phase 1 ETL</span>
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Planned metrics</h3>
          <ul className="text-sm text-slate-400 space-y-2 list-disc list-inside">
            <li>Injury-adjusted ladder position</li>
            <li>Win % vs model expectation</li>
            <li>Margin regression residuals</li>
            <li>Historical club comparisons</li>
          </ul>
        </div>
      </div>
    </>
  )
}
