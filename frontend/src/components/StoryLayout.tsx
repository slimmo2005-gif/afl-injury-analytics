import { Link, Outlet } from 'react-router-dom'
import OtherProducts from './OtherProducts'

const logoSrc = `${import.meta.env.BASE_URL}brand/slim-analytics-logo.png`

export default function StoryLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 py-4 flex flex-wrap items-center justify-between gap-4">
          <Link to="/" className="shrink-0 group" title="Slim Analytics home">
            <img
              src={logoSrc}
              alt="Slim Analytics"
              className="h-16 sm:h-20 w-auto object-contain drop-shadow-lg transition-opacity group-hover:opacity-90"
            />
          </Link>
          <nav className="flex flex-wrap items-center gap-3 text-xs sm:text-sm">
            <Link to="/" className="text-slate-400 hover:text-slate-200 transition-colors">
              Injury Luck Ladder
            </Link>
            <span className="text-slate-700">·</span>
            <Link to="/current" className="text-slate-400 hover:text-slate-200 transition-colors">
              Live season
            </Link>
            <span className="text-slate-700">·</span>
            <span className="text-afl-gold font-medium">Coleman heights</span>
          </nav>
        </div>
      </header>
      <main className="flex-1 w-full">
        <Outlet />
      </main>
      <footer className="border-t border-slate-800 py-6 text-center text-xs text-slate-500 space-y-2">
        <OtherProducts />
        <p>Slim Analytics · data from AFL Tables</p>
        <p>
          <Link to="/admin" className="text-slate-600 hover:text-slate-400">
            Admin views
          </Link>
        </p>
      </footer>
    </div>
  )
}
