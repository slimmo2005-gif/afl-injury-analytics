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
}

const accentRing = {
  gold: 'ring-afl-gold/40 bg-afl-gold/10 text-afl-gold',
  brown: 'ring-amber-700/40 bg-amber-900/20 text-amber-200',
  emerald: 'ring-emerald-500/40 bg-emerald-500/10 text-emerald-300',
}

export default function PlayerPhoto({
  name,
  photoUrl,
  className = 'w-full h-56 object-cover object-top',
  accent = 'gold',
}: PlayerPhotoProps) {
  const [failed, setFailed] = useState(false)
  const src = resolvePhotoUrl(photoUrl)

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

  return (
    <img
      src={src}
      alt={name}
      className={`rounded-xl object-cover object-top bg-slate-800 ${className}`}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  )
}
