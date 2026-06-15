import { Link, Outlet } from 'react-router-dom'
import { useMetricsContext } from '../context/MetricsContext'
import BrandHeader from './BrandHeader'

export default function ClubLayout() {
  const { source, data, loading } = useMetricsContext()
  const badge =
    source === 'live'
      ? { text: `Live · ${data.meta.season}`, className: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' }
      : { text: 'Demo data', className: 'bg-amber-500/20 text-amber-300 border-amber-500/30' }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex flex-wrap items-start justify-between gap-4">
          <BrandHeader variant="club" />
          <span className={`text-xs px-2 py-1 rounded border shrink-0 ${badge.className}`}>
            {loading ? 'Loading…' : badge.text}
          </span>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-slate-800 py-4 text-center text-xs text-slate-500 space-y-1">
        <p>Slim Analytics · weekly ETL from availability DB</p>
        <p>
          <Link to="/admin" className="text-slate-600 hover:text-slate-400">
            Admin views
          </Link>
        </p>
      </footer>
    </div>
  )
}
