export const DATA_COMPLETENESS = [
  { year: 2025, stars: 5 },
  { year: 2024, stars: 5 },
  { year: 2023, stars: 5 },
  { year: 2022, stars: 4, note: 'Reserves coverage still maturing in some states' },
  { year: 2021, stars: 4, note: 'First full season of VFL/SANFL tracking' },
] as const

const SOURCES = [
  {
    name: 'Squiggle',
    url: 'https://api.squiggle.com.au',
    description: 'Fixtures, results, and ladder positions',
  },
  {
    name: 'Fryzigg AFL',
    url: 'http://www.fryziggafl.net/',
    description: 'Player participation and per-game stats',
  },
  {
    name: 'Draftguru',
    url: 'https://www.draftguru.com.au',
    description: 'National draft picks for player potential scores',
  },
  {
    name: 'VFL stats (aflmstats)',
    url: 'https://vfl.aflmstats.com',
    description: 'VFL reserves participation from 2021',
  },
  {
    name: 'SANFL',
    url: 'https://sanfl.com.au',
    description: 'South Australian reserves participation',
  },
] as const

function StarRating({ count }: { count: number }) {
  return (
    <span className="text-amber-400 tracking-tight" aria-label={`${count} out of 5 stars`}>
      {'★'.repeat(count)}
      <span className="text-slate-700">{'★'.repeat(5 - count)}</span>
    </span>
  )
}

export default function ClubPageFooter() {
  return (
    <footer className="mt-12 space-y-8 border-t border-slate-800 pt-8">
      <section>
        <h3 className="text-sm font-medium text-slate-300 mb-3">Sources</h3>
        <p className="text-sm text-slate-400 mb-4 leading-relaxed">
          This site is built from publicly available AFL data. Thank you to the maintainers and
          communities behind these projects — we could not publish this without them.
        </p>
        <ul className="space-y-2">
          {SOURCES.map((src) => (
            <li key={src.name} className="text-sm">
              <a
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-afl-gold hover:text-yellow-300 transition-colors"
              >
                {src.name}
              </a>
              <span className="text-slate-500"> — {src.description}</span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className="text-sm font-medium text-slate-300 mb-3">Data completeness</h3>
        <p className="text-sm text-slate-500 mb-4">
          Subjective quality rating for unavailability tracking by season. Five stars means we are
          confident in fixture matching, participation, and reserves data for that year.
        </p>
        <ul className="space-y-2">
          {DATA_COMPLETENESS.map((row) => (
            <li key={row.year} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
              <span className="text-slate-300 w-12 tabular-nums">{row.year}:</span>
              <StarRating count={row.stars} />
              {'note' in row && row.note && (
                <span className="text-slate-500 text-xs w-full sm:w-auto sm:ml-1">{row.note}</span>
              )}
            </li>
          ))}
        </ul>
      </section>
    </footer>
  )
}
