import { NavLink, Outlet } from 'react-router-dom'

const nav = [
  { to: '/', label: 'League' },
  { to: '/club', label: 'Club' },
  { to: '/season', label: 'Season' },
  { to: '/player', label: 'Player' },
  { to: '/trends', label: 'Trends' },
  { to: '/model', label: 'Model' },
]

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="text-2xl" aria-hidden>🏉</span>
            <div>
              <h1 className="text-lg font-semibold text-afl-gold tracking-tight">
                AFL Unavailability Analytics
              </h1>
              <p className="text-xs text-slate-400">Injury-adjusted team performance · Wireframe MVP</p>
            </div>
          </div>
          <span className="text-xs px-2 py-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
            Demo data
          </span>
        </div>
        <nav className="max-w-7xl mx-auto px-4 flex gap-1 overflow-x-auto pb-2">
          {nav.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
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
        </nav>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-slate-800 py-4 text-center text-xs text-slate-500">
        Phase 1: availability DB · Phase 2: PVS & regression · Static JSON from weekly ETL
      </footer>
    </div>
  )
}
