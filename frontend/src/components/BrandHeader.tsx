import { Link } from 'react-router-dom'

const logoSrc = `${import.meta.env.BASE_URL}brand/slim-analytics-logo.png`

interface BrandHeaderProps {
  variant?: 'club' | 'admin'
}

export default function BrandHeader({ variant = 'club' }: BrandHeaderProps) {
  const isClub = variant === 'club'

  return (
    <div className={`flex flex-wrap items-center gap-4 ${isClub ? 'gap-6' : 'gap-4'}`}>
      <Link to="/" className="shrink-0 group" title="Slim Analytics — The Injury Luck Ladder">
        <img
          src={logoSrc}
          alt="Slim Analytics"
          className={
            isClub
              ? 'h-[6.8rem] sm:h-[8.5rem] w-auto object-contain drop-shadow-lg transition-opacity group-hover:opacity-90'
              : 'h-[4.25rem] w-auto object-contain'
          }
        />
      </Link>
      <div className="min-w-0">
        <h1
          className={
            isClub
              ? 'text-[2.125rem] sm:text-[2.55rem] font-semibold text-afl-gold tracking-tight leading-tight'
              : 'text-[1.9rem] font-semibold text-afl-gold tracking-tight leading-tight'
          }
        >
          The Injury Luck Ladder
        </h1>
        <p className="text-[1.275rem] text-slate-400 mt-1">
          {isClub ? 'Slim Analytics · club injury & performance' : 'Slim Analytics · admin workspace'}
        </p>
      </div>
    </div>
  )
}
