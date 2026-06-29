import { Link, Outlet } from 'react-router-dom'
import OtherProducts from './OtherProducts'
import SiteNavSelect from './SiteNavSelect'

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
          <SiteNavSelect />
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
