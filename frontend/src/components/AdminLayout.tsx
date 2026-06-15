import { NavLink, Outlet } from 'react-router-dom'
import { useMetricsContext } from '../context/MetricsContext'
import BrandHeader from './BrandHeader'

const nav = [
  { to: '/admin', label: 'League', end: true },
  { to: '/admin/insights', label: 'Injury insights' },
  { to: '/admin/season', label: 'Season' },
  { to: '/admin/player', label: 'Player' },
  { to: '/admin/trends', label: 'Trends' },
  { to: '/admin/model', label: 'Model' },
  { to: '/admin/roles', label: 'Role impact' },
  { to: '/admin/analytics', label: 'Analytics' },
]

export default function AdminLayout() {
  const { source, data, loading } = useMetricsContext()
  const badge =
    source === 'live'
      ? { text: `Live · ${data.meta.season}`, className: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' }
      : { text: 'Demo data', className: 'bg-amber-500/20 text-amber-300 border-amber-500/30' }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
          <BrandHeader variant="admin" />
          <span className={`text-xs px-2 py-1 rounded border ${badge.className}`}>
            {loading ? 'Loading metrics…' : badge.text}
          </span>
        </div>
        <nav className="max-w-7xl mx-auto px-4 flex gap-1 overflow-x-auto pb-2">
          {nav.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-md text-sm whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-afl-green text-afl-gold font-medium'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
          <NavLink
            to="/"
            className="px-3 py-1.5 rounded-md text-sm whitespace-nowrap text-slate-500 hover:text-slate-300 ml-auto"
          >
            ← Club view
          </NavLink>
        </nav>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-slate-800 py-4 text-center text-xs text-slate-500">
        Admin workspace · Phase 1 availability · Phase 2 PVS & regression
      </footer>
    </div>
  )
}
