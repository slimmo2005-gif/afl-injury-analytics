import type { ReactNode } from 'react'
import PlayerPhoto from './PlayerPhoto'

interface HeroCardProps {
  eyebrow: string
  name: string
  club: string
  year?: number
  heightLabel: string
  photoUrl?: string | null
  accent: 'gold' | 'brown' | 'emerald'
  photoFit?: 'cover' | 'contain'
  children?: ReactNode
  footer?: ReactNode
  highlight?: ReactNode
}

export default function HeroCard({
  eyebrow,
  name,
  club,
  year,
  heightLabel,
  photoUrl,
  accent,
  photoFit = 'cover',
  children,
  footer,
  highlight,
}: HeroCardProps) {
  const border =
    accent === 'gold'
      ? 'border-afl-gold/30 hover:border-afl-gold/50'
      : accent === 'emerald'
        ? 'border-emerald-500/30 hover:border-emerald-500/50'
        : 'border-amber-700/30 hover:border-amber-600/50'

  return (
    <article
      className={`group rounded-2xl border bg-slate-900/60 p-5 sm:p-6 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-black/30 ${border}`}
    >
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500 mb-3">{eyebrow}</p>
      <PlayerPhoto
        name={name}
        photoUrl={photoUrl}
        accent={accent}
        fit={photoFit}
        className="w-full h-52 sm:h-64 mb-4"
      />
      <h3 className="text-2xl sm:text-3xl font-semibold text-slate-100">{name}</h3>
      <p className="text-slate-400 mt-1">
        {club}
        {year != null ? ` · ${year}` : ''}
      </p>
      <div className="mt-4 flex flex-wrap gap-4 text-sm">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-500">Height</p>
          <p className="text-lg font-semibold text-slate-100 tabular-nums">{heightLabel}</p>
        </div>
        {children}
      </div>
      {highlight && (
        <p className="mt-4 rounded-lg border border-afl-gold/30 bg-afl-gold/10 px-3 py-2 text-sm text-afl-gold leading-snug">
          {highlight}
        </p>
      )}
      {footer && <p className="mt-3 text-xs text-slate-500 leading-relaxed">{footer}</p>}
    </article>
  )
}
