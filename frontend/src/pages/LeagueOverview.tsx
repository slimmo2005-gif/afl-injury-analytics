import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import FilterBar from '../components/FilterBar'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import mock from '../data/mockMetrics.json'
import type { MockMetrics } from '../types/metrics'

const data = mock as MockMetrics

export default function LeagueOverview() {
  const { leagueOverview, clubRankings } = data

  return (
    <>
      <PageHeader
        title="League overview"
        subtitle="Which clubs lose the most player value to unavailability, and who beats injury-adjusted expectations?"
      />
      <FilterBar />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Avg unavailable PVS / club" value={leagueOverview.avgUnavailableValue} accent="gold" />
        <StatCard label="Above expectation" value={leagueOverview.clubsAboveExpectation} hint="Outperform injury model" accent="green" />
        <StatCard label="Below expectation" value={leagueOverview.clubsBelowExpectation} accent="red" />
        <StatCard
          label="Unavailable ↔ wins"
          value={leagueOverview.correlationUnavailableToWins.toFixed(2)}
          hint={`Highest loss: ${leagueOverview.topUnavailableClub}`}
        />
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-4">Season unavailable value vs injury-adjusted wins</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={clubRankings} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="club" tick={{ fill: '#94a3b8', fontSize: 11 }} angle={-25} textAnchor="end" height={60} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#f5c518' }}
              />
              <Bar dataKey="unavailableValue" name="Unavailable PVS" fill="#0d3d2e" radius={[4, 4, 0, 0]} />
              <Bar dataKey="actualWins" name="Actual wins" fill="#f5c518" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  )
}
