import type { ColemanWinner } from '../../types/coleman'
import { formatHeight } from '../../lib/colemanStats'
import PlayerPhoto from './PlayerPhoto'

interface PlayerGalleryProps {
  title: string
  subtitle: string
  players: Array<ColemanWinner & { height_cm: number }>
}

function GalleryCard({ player }: { player: ColemanWinner & { height_cm: number } }) {
  const localPhoto = player.photo_url?.startsWith('coleman/')
  return (
    <article className="rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden transition hover:border-slate-700 hover:-translate-y-0.5">
      <PlayerPhoto
        name={player.player}
        photoUrl={player.photo_url}
        fit={localPhoto ? 'contain' : 'cover'}
        className="w-full h-44"
      />
      <div className="p-3">
        <h4 className="font-semibold text-slate-100">{player.player}</h4>
        <p className="text-xs text-slate-500 mt-0.5">
          {player.club} · {player.year}
        </p>
        <dl className="mt-2 grid grid-cols-2 gap-2 text-xs">
          <div>
            <dt className="text-slate-500">Goals</dt>
            <dd className="text-slate-200 font-medium tabular-nums">{player.goals}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Height</dt>
            <dd className="text-slate-200 font-medium tabular-nums">{player.height_cm} cm</dd>
          </div>
        </dl>
      </div>
    </article>
  )
}

export default function PlayerGallery({ title, subtitle, players }: PlayerGalleryProps) {
  return (
    <section>
      <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
      <p className="text-sm text-slate-500 mt-1 mb-4">{subtitle}</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {players.map((p) => (
          <GalleryCard key={`${p.year}-${p.player}`} player={p} />
        ))}
      </div>
    </section>
  )
}

export { formatHeight }
