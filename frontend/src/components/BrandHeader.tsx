import { Link } from 'react-router-dom'
import { UKRAINE_TRACKER_URL } from '../constants'

const logoSrc = `${import.meta.env.BASE_URL}brand/slim-analytics-logo.png`

interface BrandHeaderProps {
  variant?: 'club' | 'admin'
}

export default function BrandHeader({ variant = 'club' }: BrandHeaderProps) {
  const isClub = variant === 'club'

  return (
    <div className={`flex flex-wrap items-center gap-4 ${isClub ? 'gap-6' : 'gap-4'}`}>
      <Link to="/" className="shrink-0 group" title="Slim Analytics — AFL club view">
        <img
          src={logoSrc}
          alt="Slim Analytics"
          className={
            isClub
              ? 'h-16 sm:h-20 w-auto object-contain drop-shadow-lg transition-opacity group-hover:opacity-90'
              : 'h-10 w-auto object-contain'
          }
        />
      </Link>
      <div className="min-w-0">
        <h1
          className={
            isClub
              ? 'text-xl sm:text-2xl font-semibold text-afl-gold tracking-tight'
              : 'text-lg font-semibold text-afl-gold tracking-tight'
          }
        >
          AFL Unavailability Analytics
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          {isClub ? 'Club injury & performance view' : 'Admin analytics workspace'}
        </p>
        <a
          href={UKRAINE_TRACKER_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 mt-2 text-xs text-slate-400 hover:text-cyan-300 transition-colors"
        >
          <span aria-hidden>🗺️</span>
          Ukraine War Territory Tracker
          <span aria-hidden className="text-[10px]">↗</span>
        </a>
      </div>
    </div>
  )
}
