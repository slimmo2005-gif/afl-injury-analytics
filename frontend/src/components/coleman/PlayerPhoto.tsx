import { useState } from 'react'

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export function resolvePhotoUrl(url: string | null | undefined): string | null {
  if (!url) return null
  if (url.startsWith('http')) return url
  return `${import.meta.env.BASE_URL}${url.replace(/^\//, '')}`
}

interface PlayerPhotoProps {
  name: string
  photoUrl?: string | null
  className?: string
  accent?: 'gold' | 'brown' | 'emerald'
  /** contain = show full portrait (vintage cards); cover = crop to fill */
  fit?: 'cover' | 'contain'
}

const accentRing = {
  gold: 'ring-afl-gold/40 bg-afl-gold/10 text-afl-gold',
  brown: 'ring-amber-700/40 bg-amber-900/20 text-amber-200',
  emerald: 'ring-emerald-500/40 bg-emerald-500/10 text-emerald-300',
}

export default function PlayerPhoto({
  name,
  photoUrl,
  className = 'w-full h-56',
  accent = 'gold',
  fit = 'cover',
}: PlayerPhotoProps) {
  const [failed, setFailed] = useState(false)
  const src = resolvePhotoUrl(photoUrl)
  const isContain = fit === 'contain'
  const imgFit = isContain ? 'object-contain object-center' : 'object-cover object-top'

  if (!src || failed) {
    return (
      <div
        className={`flex items-center justify-center rounded-xl ring-2 ${accentRing[accent]} ${className}`}
        aria-label={`${name} photo unavailable`}
      >
        <span className="text-4xl font-bold tracking-tight">{initials(name)}</span>
      </div>
    )
  }

  if (isContain) {
    return (
      <div className={`rounded-xl bg-slate-950/80 overflow-hidden ${className}`}>
        <img
          src={src}
          alt={name}
          className={`w-full h-full ${imgFit} p-1 sm:p-2`}
          loading="lazy"
          onError={() => setFailed(true)}
        />
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={name}
      className={`rounded-xl bg-slate-800 ${imgFit} ${className}`}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  )
}
