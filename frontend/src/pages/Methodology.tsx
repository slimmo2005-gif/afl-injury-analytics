import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'
import { DATA_COMPLETENESS } from '../components/ClubPageFooter'

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="text-lg font-semibold text-slate-200 mb-3">{title}</h2>
      <div className="text-sm text-slate-400 space-y-3 leading-relaxed">{children}</div>
    </section>
  )
}

export default function Methodology() {
  return (
    <article className="max-w-3xl">
      <Link
        to="/"
        className="text-xs text-slate-500 hover:text-slate-300 transition-colors mb-4 inline-block"
      >
        ← Back to club view
      </Link>

      <h1 className="text-2xl sm:text-3xl font-bold text-slate-100 mb-2">Methodology</h1>
      <p className="text-slate-400 text-sm mb-8 leading-relaxed">
        How we measure player unavailability, weight it by player importance, and compare clubs to
        the final ladder. This is an observational model — not an official injury report.
      </p>

      <Section title="What we are trying to answer">
        <p>
          Did a club&apos;s ladder finish make sense given how much important player value they
          missed during the season? We do not claim to know <em>why</em> a player was out — only
          that they were not selected for AFL that week while on the club&apos;s fixture list.
        </p>
      </Section>

      <Section title="What counts as unavailable">
        <p>
          For every scheduled home-and-away round on a club&apos;s fixture, we check whether each
          listed player was selected in the AFL team. Status falls into three buckets:
        </p>
        <ul className="list-disc pl-5 space-y-2">
          <li>
            <strong className="text-slate-300">AFL selected</strong> — available for our purposes.
          </li>
          <li>
            <strong className="text-slate-300">VFL / SANFL / WAFL only</strong> — played reserves
            but not AFL. Tracked separately as &ldquo;VFL-only&rdquo; weeks and{' '}
            <em>excluded</em> from injury-impact rankings (rehab stints should not inflate
            unavailability).
          </li>
          <li>
            <strong className="text-slate-300">Neither AFL nor reserves</strong> — counted as
            unavailable. This is mostly injury, but also includes suspensions, personal leave,
            omission, and any other reason a fit-listed player did not play.
          </li>
        </ul>
        <p>
          We do not use official club injury reports. Availability is inferred from participation
          records only.
        </p>
      </Section>

      <Section title="Building the fixture list">
        <p>
          Squiggle provides fixtures and ladder positions. Fryzigg provides who played each AFL game.
          We build availability from <strong className="text-slate-300">each club&apos;s own
          fixture</strong>, not a league-wide round list, so bye weeks, Opening Round, and finals
          blocks do not create false absences. Home-and-away scope excludes rounds with very few
          league games (finals clusters).
        </p>
        <p>
          Players who appeared recently but sat out a round without playing reserves are flagged as{' '}
          <strong className="text-slate-300">intermittent</strong> absences — a softer signal than
          a long-term unavailable stint, but still counted in PVS lost.
        </p>
      </Section>

      <Section title="Player Value Score (PVS)">
        <p>
          Not all missed games are equal. Losing a best-22 midfielder for ten weeks matters more
          than losing a depth player for two. PVS estimates how valuable each player is to their
          club.
        </p>
        <p>
          <strong className="text-slate-300">Performance component</strong> — a weighted blend of
          season per-game stats (disposals, goals, tackles, clearances, marks, etc.), normalised so
          league leaders score around 7. Effective disposals (disposals × disposal efficiency) are
          included so quality of ball use matters.
        </p>
        <p>
          <strong className="text-slate-300">Draft potential</strong> — for players under 25, PVS
          blends performance with a draft-pick curve (earlier national draft picks score higher).
          The blend ramps from age 18 (30% performance weight) to age 25 (100% performance). Potential
          can <em>raise</em> a young player&apos;s score but never reduces a proven performer&apos;s
          score.
        </p>
        <p className="font-mono text-xs text-slate-500 bg-slate-900/60 border border-slate-800 rounded-lg p-3">
          PVS = max(performance, w(age) × performance + (1 − w(age)) × potential × 0.75)
        </p>
        <p>
          When a player is unavailable, we multiply their PVS by an injury weight that can bump
          stars who returned late in the season (limited sample games would otherwise understate
          their value).
        </p>
      </Section>

      <Section title="Injury-impact rank">
        <p>
          Each club&apos;s season total of unavailable PVS (excluding VFL-only weeks) is ranked
          against the rest of the league.{' '}
          <strong className="text-slate-300">Rank 1 = healthiest list</strong> (fewest PVS lost).{' '}
          <strong className="text-slate-300">Rank 18 = hardest hit.</strong>
        </p>
        <p>
          We also track top-5 and top-10 unavailable PVS — how much of the toll came from your
          most important players.
        </p>
      </Section>

      <Section title="Rank delta (ladder vs injury luck)">
        <p>
          Rank delta = ladder position − injury-impact rank. A{' '}
          <strong className="text-slate-300">negative</strong> delta means the club finished{' '}
          <em>higher</em> on the ladder than their unavailability suggested (outperformed). A{' '}
          <strong className="text-slate-300">positive</strong> delta means they finished lower
          (underperformed).
        </p>
        <p>
          We only use strong language in headlines when the gap exceeds four ladder places. Extreme
          mismatches — like a club with the league&apos;s best injury luck finishing near the
          bottom — are called out explicitly when they are the largest in our 2021–2025 window.
        </p>
        <p>
          Rank delta is descriptive, not predictive. Form, fixture, coaching, list quality, and
          players outperforming their baseline all matter alongside injuries.
        </p>
      </Section>

      <Section title="Data sources">
        <ul className="list-disc pl-5 space-y-2">
          <li>
            <a
              href="https://api.squiggle.com.au"
              className="text-afl-gold hover:text-yellow-300"
              target="_blank"
              rel="noopener noreferrer"
            >
              Squiggle
            </a>{' '}
            — fixtures, results, ladder
          </li>
          <li>
            <a
              href="http://www.fryziggafl.net/"
              className="text-afl-gold hover:text-yellow-300"
              target="_blank"
              rel="noopener noreferrer"
            >
              Fryzigg AFL
            </a>{' '}
            — AFL participation and stats
          </li>
          <li>
            <a
              href="https://www.draftguru.com.au"
              className="text-afl-gold hover:text-yellow-300"
              target="_blank"
              rel="noopener noreferrer"
            >
              Draftguru
            </a>{' '}
            — national draft picks
          </li>
          <li>
            <a
              href="https://vfl.aflmstats.com"
              className="text-afl-gold hover:text-yellow-300"
              target="_blank"
              rel="noopener noreferrer"
            >
              VFL stats
            </a>{' '}
            — VFL reserves from 2021
          </li>
          <li>
            <a
              href="https://sanfl.com.au"
              className="text-afl-gold hover:text-yellow-300"
              target="_blank"
              rel="noopener noreferrer"
            >
              SANFL
            </a>{' '}
            — South Australian reserves
          </li>
        </ul>
        <p>Thank you to everyone who maintains these public datasets.</p>
      </Section>

      <Section title="Known limitations">
        <ul className="list-disc pl-5 space-y-2">
          <li>No official injury diagnoses — we infer absence from non-selection.</li>
          <li>
            VFL/SANFL/WAFL coverage is strongest from 2021; earlier seasons rely on AFL participation
            only.
          </li>
          <li>
            Player name matching across sources can miss fringe cases; we log and reconcile where
            possible.
          </li>
          <li>
            PVS is a model, not a market value or AFL Player Rating. It is designed to be
            explainable, not perfect.
          </li>
          <li>
            SANFL club-to-AFL mappings (e.g. Port Adelaide ↔ Port Melbourne) require manual alignment.
          </li>
        </ul>
      </Section>

      <Section title="Data completeness by season">
        <ul className="space-y-2">
          {DATA_COMPLETENESS.map((row) => (
            <li key={row.year} className="flex flex-wrap gap-x-2">
              <span className="text-slate-300 w-12">{row.year}:</span>
              <span className="text-amber-400">{'★'.repeat(row.stars)}</span>
              <span className="text-slate-600">{'★'.repeat(5 - row.stars)}</span>
              {'note' in row && row.note && (
                <span className="text-slate-500 text-xs">— {row.note}</span>
              )}
            </li>
          ))}
        </ul>
      </Section>

      <p className="text-xs text-slate-600 border-t border-slate-800 pt-6">
        Pipeline refreshes weekly. Metrics export to static JSON for this site.
      </p>
    </article>
  )
}
