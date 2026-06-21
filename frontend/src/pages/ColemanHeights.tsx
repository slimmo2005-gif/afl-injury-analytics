import { useEffect, useMemo } from 'react'
import ComparisonSilhouettes from '../components/coleman/ComparisonSilhouettes'
import FunFacts from '../components/coleman/FunFacts'
import HeightDistributionChart from '../components/coleman/HeightDistributionChart'
import HeroCard from '../components/coleman/HeroCard'
import NotableRecords from '../components/coleman/NotableRecords'
import PlayerGallery from '../components/coleman/PlayerGallery'
import TimelineChart from '../components/coleman/TimelineChart'
import StatCard from '../components/StatCard'
import { useColemanHeights } from '../hooks/useColemanHeights'
import {
  computeColemanStats,
  formatHeight,
  generateFunFacts,
  shortestWinners,
  tallestWinners,
  timelinePoints,
} from '../lib/colemanStats'

const SOCIAL_IMAGE = `${import.meta.env.BASE_URL}coleman/social-share.png`

export default function ColemanHeights() {
  const { data, loading, error } = useColemanHeights()

  const stats = useMemo(() => (data ? computeColemanStats(data) : null), [data])
  const facts = useMemo(
    () => (stats && data ? generateFunFacts(stats, data.challenger) : []),
    [stats, data],
  )
  const timeline = useMemo(
    () => (data ? timelinePoints(data.winners, data.challenger) : []),
    [data],
  )
  const shortFive = useMemo(() => (data ? shortestWinners(data.winners, 5) : []), [data])
  const tallFive = useMemo(() => (data ? tallestWinners(data.winners, 5) : []), [data])

  useEffect(() => {
    document.title = 'The Height of Coleman Medal Winners · Slim Analytics'
    const desc =
      'If Nick Watson wins the 2026 Coleman Medal, he could become the shortest Coleman Medallist on record — shorter than Leigh Matthews (178 cm, 1975).'
    const setMeta = (prop: string, content: string, isProperty = false) => {
      const attr = isProperty ? 'property' : 'name'
      let el = document.querySelector(`meta[${attr}="${prop}"]`)
      if (!el) {
        el = document.createElement('meta')
        el.setAttribute(attr, prop)
        document.head.appendChild(el)
      }
      el.setAttribute('content', content)
    }
    setMeta('description', desc)
    setMeta('og:title', 'The Height of Coleman Medal Winners', true)
    setMeta('og:description', desc, true)
    setMeta('og:image', new URL(SOCIAL_IMAGE, window.location.origin).href, true)
    setMeta('twitter:card', 'summary_large_image')
    setMeta('twitter:title', 'Could Nick Watson become the shortest Coleman Medallist on record?')
    setMeta('twitter:description', desc)
    setMeta('twitter:image', new URL(SOCIAL_IMAGE, window.location.origin).href)
  }, [])

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-16 text-center text-slate-400">
        Loading Coleman height data…
      </div>
    )
  }

  if (error || !data || !stats) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-16 text-center text-red-400">
        {error ?? 'Unable to load data'}
      </div>
    )
  }

  const { challenger, meta } = data
  const roy = stats.royPark
  const shortestColeman = stats.shortestColemanMedallist

  const watsonHighlight =
    shortestColeman && challenger.height_cm < shortestColeman.height_cm
      ? `If Watson wins, he becomes the shortest Coleman Medallist on record — ${shortestColeman.height_cm - challenger.height_cm} cm shorter than ${shortestColeman.player} (${shortestColeman.year}).`
      : shortestColeman
        ? `If Watson wins at ${challenger.height_cm} cm, he would join a small group of Coleman Medallists under 180 cm. The shortest on record is ${shortestColeman.player} (${shortestColeman.height_cm} cm, ${shortestColeman.year}).`
        : 'If Watson wins, he would add another chapter to the height story of league leading goalkickers.'

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:py-12 space-y-12 sm:space-y-16">
      <header className="text-center max-w-3xl mx-auto">
        <p className="text-xs uppercase tracking-[0.25em] text-afl-gold mb-3">Slim Analytics</p>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-semibold text-slate-100 tracking-tight leading-tight">
          The Height of Coleman Medal Winners
        </h1>
        <p className="text-base sm:text-lg text-slate-300 mt-4 leading-relaxed">
          Nick Watson has a chance to become the shortest{' '}
          <strong className="font-semibold text-slate-200">Coleman Medallist</strong> on record
          {shortestColeman ? (
            <>
              {' '}
              — shorter than {shortestColeman.player} ({shortestColeman.height_cm} cm,{' '}
              {shortestColeman.year}).
            </>
          ) : (
            '.'
          )}
        </p>
        <p className="text-xs text-slate-500 mt-4 leading-relaxed">
          *Heights from AFL Tables where recorded. Vin Coutie (1904) has no reliable height. The
          Coleman Medal was first presented in {meta.awardHistory.colemanFirstPresented}; league
          leaders from {meta.awardHistory.colemanRetrospectiveFrom}–1980 were recognised as
          retrospective Coleman Medallists in {meta.awardHistory.retrospectiveRecognitionYear}.
          Earlier leaders (1897–{meta.awardHistory.leadingGoalkickerMedalThrough}) received the
          separate Leading Goalkicker Medal — Roy Park (1913) was one of those, not a Coleman
          Medallist.
        </p>
      </header>

      <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 sm:p-5 text-sm text-slate-400 leading-relaxed">
        <h2 className="text-xs uppercase tracking-wider text-afl-gold mb-2">How the awards work</h2>
        <p>{meta.awardHistory.summary}</p>
        <ul className="mt-3 space-y-1.5 list-disc list-inside text-xs text-slate-500">
          <li>
            <span className="text-slate-400">1981+</span> — Coleman Medal presented at end of season
          </li>
          <li>
            <span className="text-slate-400">1955–1980</span> — retrospective Coleman Medallists
            (recognised 2001, medals presented 2004)
          </li>
          <li>
            <span className="text-slate-400">1897–1954</span> — Leading Goalkicker Medallists (a
            different award)
          </li>
        </ul>
      </section>

      <section className="grid lg:grid-cols-2 gap-5 sm:gap-6">
        <HeroCard
          eyebrow="Shortest Leading Goalkicker Medallist"
          name="Roy Park"
          club="University"
          year={1913}
          heightLabel={formatHeight(roy?.height_cm ?? null)}
          photoUrl={roy?.photo_url ?? 'coleman/roy-park.png'}
          accent="brown"
          photoFit="contain"
          footer="Leading Goalkicker Medallist (1897–1954 era) — not a Coleman Medal. Still the shortest recorded league leading goalkicker with a known height."
        >
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">Nickname</p>
            <p className="text-lg font-semibold text-amber-200">&ldquo;Little Doc&rdquo;</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">Award</p>
            <p className="text-sm font-medium text-slate-300">Leading Goalkicker Medal</p>
          </div>
        </HeroCard>

        <HeroCard
          eyebrow="Current challenger"
          name={challenger.player}
          club={challenger.club}
          heightLabel={formatHeight(challenger.height_cm)}
          photoUrl={challenger.photo_url}
          accent="emerald"
          highlight={watsonHighlight}
        >
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">Current goals</p>
            <p className="text-lg font-semibold text-slate-100 tabular-nums">{challenger.current_goals}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">Coleman position</p>
            <p className="text-lg font-semibold text-emerald-300 tabular-nums">#{challenger.coleman_position}</p>
          </div>
          {challenger.nickname && (
            <div>
              <p className="text-xs uppercase tracking-wider text-slate-500">Nickname</p>
              <p className="text-lg font-semibold text-emerald-200">&ldquo;{challenger.nickname}&rdquo;</p>
            </div>
          )}
        </HeroCard>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-200 mb-4">By the numbers</h2>
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          <StatCard label="Coleman Medallists" value={stats.totalColemanMedallists} accent="gold" />
          <StatCard
            label="Leading GK Medallists"
            value={stats.totalLeadingGoalkickerMedallists}
            hint="1897–1954"
            accent="orange"
          />
          <StatCard
            label="Shortest Coleman Medallist"
            value={
              stats.shortestColemanMedallist
                ? `${stats.shortestColemanMedallist.height_cm} cm`
                : '—'
            }
            hint={
              stats.shortestColemanMedallist
                ? `${stats.shortestColemanMedallist.player} (${stats.shortestColemanMedallist.year})`
                : undefined
            }
            accent="green"
          />
          <StatCard
            label="Shortest Leading GK Medallist"
            value={
              stats.shortestLeadingGoalkickerMedallist
                ? `${stats.shortestLeadingGoalkickerMedallist.height_cm} cm`
                : '—'
            }
            hint={
              stats.shortestLeadingGoalkickerMedallist
                ? `${stats.shortestLeadingGoalkickerMedallist.player} (${stats.shortestLeadingGoalkickerMedallist.year})`
                : undefined
            }
            accent="orange"
          />
          <StatCard
            label="Tallest Coleman Medallist"
            value={stats.tallest ? `${stats.tallest.height_cm} cm` : '—'}
            hint={stats.tallest ? stats.tallest.player : undefined}
            accent="neutral"
          />
          <StatCard
            label="Average Coleman height"
            value={stats.averageHeight != null ? `${stats.averageHeight} cm` : '—'}
            hint={`${stats.withHeight} with height on file`}
            accent="gold"
          />
        </div>
      </section>

      <HeightDistributionChart bands={stats.heightBands} />

      <TimelineChart points={timeline} />

      <section>
        <h2 className="text-lg font-semibold text-slate-200 mb-4">Notable records</h2>
        <NotableRecords stats={stats} />
      </section>

      <FunFacts facts={facts} />

      <section className="space-y-10">
        <PlayerGallery
          title="Shortest five (all awards)"
          subtitle="Leading goalkickers with the lowest recorded heights — Coleman Medallists and Leading Goalkicker Medallists combined"
          players={shortFive}
        />
        <PlayerGallery
          title="Tallest five Coleman Medallists"
          subtitle="Coleman Medallists (1955+) with the highest recorded heights"
          players={tallFive}
        />
      </section>

      <ComparisonSilhouettes
        people={[
          { label: 'Nick Watson', height_cm: challenger.height_cm, accent: '#34d399', note: '2026 challenger' },
          {
            label: 'Avg Coleman Medallist',
            height_cm: stats.averageHeight,
            accent: '#0d3d2e',
          },
          {
            label: shortestColeman?.player ?? 'Shortest Coleman',
            height_cm: shortestColeman?.height_cm ?? null,
            accent: '#64748b',
            note: shortestColeman ? `${shortestColeman.year} · Coleman` : undefined,
          },
          {
            label: 'Roy Park',
            height_cm: roy?.height_cm ?? null,
            accent: '#f5c518',
            note: 'Leading GK Medal · 1913',
          },
          {
            label: 'Harry McKay',
            height_cm: stats.harryMcKay?.height_cm ?? null,
            accent: '#22d3ee',
            note: 'Tallest Coleman (2021)',
          },
        ]}
      />

      <section className="rounded-xl border border-slate-800 bg-slate-900/30 p-4 text-xs text-slate-500 leading-relaxed">
        <p>
          Heights sourced from{' '}
          <a
            href="https://afltables.com/afl/stats/alltime/leadinggk.html"
            className="text-slate-400 hover:text-afl-gold underline"
            target="_blank"
            rel="noreferrer"
          >
            AFL Tables
          </a>
          . Award history per AFL /{' '}
          <a
            href="https://en.wikipedia.org/wiki/Coleman_Medal"
            className="text-slate-400 hover:text-afl-gold underline"
            target="_blank"
            rel="noreferrer"
          >
            Wikipedia
          </a>
          . The 2026 Coleman race is in progress — Watson&apos;s goals and ladder position are updated
          manually in the dataset.
        </p>
      </section>
    </div>
  )
}
