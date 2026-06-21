import type {
  ColemanChallenger,
  ColemanHeightsBundle,
  ColemanStats,
  ColemanWinner,
  HeightBand,
} from '../types/coleman'

const HEIGHT_BANDS = [
  { label: 'Under 170 cm', min: 0, max: 169 },
  { label: '170–179 cm', min: 170, max: 179 },
  { label: '180–189 cm', min: 180, max: 189 },
  { label: '190–199 cm', min: 190, max: 199 },
  { label: '200 cm+', min: 200, max: null },
] as const

export function isCompletedColemanMedallist(w: ColemanWinner): boolean {
  return w.coleman_medal && !w.season_incomplete
}

export function isLeadingGoalkickerMedallist(w: ColemanWinner): boolean {
  return w.leading_goalkicker_medal && !w.season_incomplete
}

export function withRecordedHeight(w: ColemanWinner): w is ColemanWinner & { height_cm: number } {
  return w.height_cm != null
}

export function completedColemanMedallists(winners: ColemanWinner[]): ColemanWinner[] {
  return winners.filter(isCompletedColemanMedallist)
}

export function leadingGoalkickersWithHeight(
  winners: ColemanWinner[],
): Array<ColemanWinner & { height_cm: number }> {
  return winners.filter((w) => !w.season_incomplete && withRecordedHeight(w))
}

export function colemanMedallistsWithHeight(
  winners: ColemanWinner[],
): Array<ColemanWinner & { height_cm: number }> {
  return completedColemanMedallists(winners).filter(withRecordedHeight)
}

export function leadingGoalkickerMedallistsWithHeight(
  winners: ColemanWinner[],
): Array<ColemanWinner & { height_cm: number }> {
  return winners.filter((w) => isLeadingGoalkickerMedallist(w) && withRecordedHeight(w))
}

/** @deprecated alias */
export const completedMedallists = completedColemanMedallists
/** @deprecated alias */
export const medallistsWithHeight = colemanMedallistsWithHeight
/** @deprecated alias */
export const preColemanLeadersWithHeight = leadingGoalkickerMedallistsWithHeight

export function computeHeightBands(winners: ColemanWinner[]): HeightBand[] {
  const pool = colemanMedallistsWithHeight(winners)
  const total = pool.length
  return HEIGHT_BANDS.map(({ label, min, max }) => {
    const count = pool.filter((w) => {
      if (max == null) return w.height_cm >= min
      return w.height_cm >= min && w.height_cm <= max
    }).length
    return {
      label,
      min,
      max,
      count,
      pct: total ? Math.round((count / total) * 1000) / 10 : 0,
    }
  })
}

export function computeColemanStats(bundle: ColemanHeightsBundle): ColemanStats {
  const colemanWinners = completedColemanMedallists(bundle.winners)
  const lgMedallists = bundle.winners.filter(isLeadingGoalkickerMedallist)
  const withHeight = colemanMedallistsWithHeight(bundle.winners)
  const heights = withHeight.map((w) => w.height_cm)
  const bands = computeHeightBands(bundle.winners)

  const shortestColeman =
    [...colemanWinners.filter(withRecordedHeight)].sort((a, b) => a.height_cm - b.height_cm)[0] ??
    null
  const shortestLg =
    [...leadingGoalkickerMedallistsWithHeight(bundle.winners)].sort(
      (a, b) => a.height_cm - b.height_cm,
    )[0] ?? null
  const tallest = [...withHeight].sort((a, b) => b.height_cm - a.height_cm)[0] ?? null

  const mostCommonBand =
    [...bands].sort((a, b) => b.count - a.count).find((b) => b.count > 0)?.label ?? '—'

  return {
    totalColemanMedallists: colemanWinners.length,
    totalLeadingGoalkickerMedallists: lgMedallists.length,
    withHeight: withHeight.length,
    shortest: shortestColeman,
    tallest,
    averageHeight: heights.length
      ? Math.round((heights.reduce((s, h) => s + h, 0) / heights.length) * 10) / 10
      : null,
    heightBands: bands,
    under180: withHeight.filter((w) => w.height_cm < 180).length,
    over195: withHeight.filter((w) => w.height_cm > 195).length,
    mostCommonBand,
    shortestColemanMedallist: shortestColeman,
    shortestLeadingGoalkickerMedallist: shortestLg,
    royPark: bundle.winners.find((w) => w.player === 'Roy Park') ?? null,
    harryMcKay: bundle.winners.find((w) => w.player === 'Harry McKay' && w.year === 2021) ?? null,
  }
}

export type TimelinePointKind = 'coleman' | 'leading_gk_medal' | 'roy' | 'mckay' | 'watson'

export interface TimelinePoint {
  year: number
  height_cm: number
  player: string
  club: string
  goals: number
  kind: TimelinePointKind
  award: ColemanWinner['award']
  coleman_medal: boolean
}

export function timelinePoints(
  winners: ColemanWinner[],
  challenger: ColemanChallenger,
): TimelinePoint[] {
  const points: TimelinePoint[] = []

  for (const w of leadingGoalkickersWithHeight(winners)) {
    let kind: TimelinePointKind = w.coleman_medal ? 'coleman' : 'leading_gk_medal'
    if (w.player === 'Roy Park') kind = 'roy'
    if (w.player === 'Harry McKay' && w.year === 2021) kind = 'mckay'
    points.push({
      year: w.year,
      height_cm: w.height_cm,
      player: w.player,
      club: w.club,
      goals: w.goals,
      kind,
      award: w.award,
      coleman_medal: w.coleman_medal,
    })
  }

  points.push({
    year: 2026,
    height_cm: challenger.height_cm,
    player: challenger.player,
    club: challenger.club,
    goals: challenger.current_goals,
    kind: 'watson',
    award: 'Coleman Medal',
    coleman_medal: true,
  })

  return points.sort((a, b) => a.year - b.year)
}

export function generateFunFacts(stats: ColemanStats, challenger: ColemanChallenger): string[] {
  const facts: string[] = []

  facts.push(
    'The Coleman Medal was first presented in 1981. Leading goalkickers from 1955–1980 were named retrospective Coleman Medallists in 2001; 1897–1954 leaders received the Leading Goalkicker Medal.',
  )

  if (stats.under180 != null) {
    facts.push(
      `Only ${stats.under180} Coleman Medallist${stats.under180 === 1 ? '' : 's'} on record ${stats.under180 === 1 ? 'has' : 'have'} been under 180 cm.`,
    )
  }

  if (stats.averageHeight != null) {
    facts.push(
      `The average Coleman Medallist is ${stats.averageHeight} cm tall (where height is recorded).`,
    )
  }

  if (stats.tallest) {
    facts.push(
      `${stats.tallest.player} (${stats.tallest.year}) is the tallest recorded Coleman Medallist at ${stats.tallest.height_cm} cm.`,
    )
  }

  if (stats.shortestColemanMedallist) {
    facts.push(
      `${stats.shortestColemanMedallist.player} (${stats.shortestColemanMedallist.year}) is the shortest Coleman Medallist on record at ${stats.shortestColemanMedallist.height_cm} cm.`,
    )
  }

  if (stats.shortestLeadingGoalkickerMedallist?.height_cm != null) {
    facts.push(
      `${stats.shortestLeadingGoalkickerMedallist.player} ("${stats.shortestLeadingGoalkickerMedallist.nickname ?? 'Little Doc'}") is the shortest Leading Goalkicker Medallist at ${stats.shortestLeadingGoalkickerMedallist.height_cm} cm (${stats.shortestLeadingGoalkickerMedallist.year}).`,
    )
  }

  if (stats.shortestColemanMedallist && challenger.height_cm < stats.shortestColemanMedallist.height_cm) {
    facts.push(
      `If Nick Watson wins at ${challenger.height_cm} cm, he would become the shortest Coleman Medallist on record — ${stats.shortestColemanMedallist.height_cm - challenger.height_cm} cm shorter than ${stats.shortestColemanMedallist.player} (${stats.shortestColemanMedallist.year}).`,
    )
  }

  if (stats.over195 != null) {
    facts.push(
      `${stats.over195} Coleman Medallist${stats.over195 === 1 ? '' : 's'} have been taller than 195 cm.`,
    )
  }

  facts.push(`The most common height band among Coleman Medallists is ${stats.mostCommonBand}.`)

  return facts
}

export function shortestWinners(
  winners: ColemanWinner[],
  n = 5,
): Array<ColemanWinner & { height_cm: number }> {
  return winners
    .filter((w) => !w.season_incomplete && withRecordedHeight(w))
    .sort((a, b) => a.height_cm - b.height_cm || a.year - b.year)
    .slice(0, n)
}

export function tallestWinners(
  winners: ColemanWinner[],
  n = 5,
): Array<ColemanWinner & { height_cm: number }> {
  return [...colemanMedallistsWithHeight(winners)]
    .sort((a, b) => b.height_cm - a.height_cm || b.year - a.year)
    .slice(0, n)
}

export function formatHeight(cm: number | null | undefined): string {
  if (cm == null) return 'Unknown'
  const totalIn = Math.round(cm / 2.54)
  const ft = Math.floor(totalIn / 12)
  const inches = totalIn % 12
  return `${cm} cm (${ft}'${inches}")`
}
