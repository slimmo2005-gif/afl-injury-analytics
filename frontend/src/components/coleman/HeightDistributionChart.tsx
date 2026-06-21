import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { HeightBand } from '../../types/coleman'

interface HeightDistributionChartProps {
  bands: HeightBand[]
}

const BAR_COLORS = ['#f5c518', '#0d3d2e', '#164e63', '#334155', '#475569']

export default function HeightDistributionChart({ bands }: HeightDistributionChartProps) {
  const data = bands.map((b) => ({
    ...b,
    labelLine: `${b.count} (${b.pct}%)`,
  }))

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:p-6">
      <h3 className="text-sm font-medium text-slate-300 mb-1">Height distribution</h3>
      <p className="text-xs text-slate-500 mb-4">Coleman Medallists with recorded height (1955–2025)</p>
      <div className="h-72 sm:h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 48, top: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
            <XAxis type="number" allowDecimals={false} tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <YAxis
              type="category"
              dataKey="label"
              width={110}
              tick={{ fill: '#cbd5e1', fontSize: 12 }}
            />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
              formatter={(value: number, _name, item) => [
                `${value} winners (${item.payload.pct}%)`,
                'Count',
              ]}
            />
            <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={28}>
              {data.map((_, i) => (
                <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
              ))}
              <LabelList dataKey="labelLine" position="right" fill="#e2e8f0" fontSize={12} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
