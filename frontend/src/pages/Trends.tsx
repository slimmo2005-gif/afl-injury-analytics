import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import PageHeader from '../components/PageHeader'
import { useMetricsContext } from '../context/MetricsContext'

export default function Trends() {
  const { data } = useMetricsContext()
  return (
    <>
      <PageHeader
        title="Unavailability trends"
        subtitle="Lineup continuity by positional archetype and week-to-week change patterns."
      />
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-4">Continuity score by archetype</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.continuity} layout="vertical" margin={{ left: 80 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis type="number" domain={[0, 1]} tick={{ fill: '#94a3b8' }} />
              <YAxis type="category" dataKey="archetype" tick={{ fill: '#94a3b8', fontSize: 11 }} width={90} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
              <Bar dataKey="score" name="Continuity" fill="#0d3d2e" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  )
}
