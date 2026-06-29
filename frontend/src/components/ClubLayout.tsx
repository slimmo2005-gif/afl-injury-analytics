import { useEffect, useState } from 'react'
import { Link, Outlet } from 'react-router-dom'
import { logPageSessionVisit } from '../lib/analytics'
import BrandHeader from './BrandHeader'
import { FeedbackModal } from './FeedbackModal'
import FeedbackPanel from './FeedbackPanel'
import SiteNavSelect from './SiteNavSelect'

export default function ClubLayout() {
  const [showFeedback, setShowFeedback] = useState(false)

  useEffect(() => {
    logPageSessionVisit()
  }, [])

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex flex-wrap items-start justify-between gap-4">
          <BrandHeader variant="club" />
          <SiteNavSelect />
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        <Outlet />
        <div className="mt-10 max-w-md">
          <FeedbackPanel onOpen={() => setShowFeedback(true)} />
        </div>
      </main>
      <footer className="border-t border-slate-800 py-4 text-center text-xs text-slate-500 space-y-1">
        <p>Slim Analytics · weekly ETL from availability DB</p>
        <p>
          <Link to="/admin" className="text-slate-600 hover:text-slate-400">
            Admin views
          </Link>
        </p>
      </footer>
      {showFeedback && <FeedbackModal onClose={() => setShowFeedback(false)} />}
    </div>
  )
}
