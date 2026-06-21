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

export function withRecordedHeight(w: ColemanWinner): w is ColemanWinner & { height_cm: number } {
  return w.height_cm != null
}

export function completedMedallists(winners: ColemanWinner[]): ColemanWinner[] {
  return winners.filter(isCompletedColemanMedallist)
}

export function medallistsWithHeight(winners: ColemanWinner[]): Array<ColemanWinner & { height_cm: number }> {
  return completedMedallists(winners).filter(withRecordedHeight)
}

export function computeHeightBands(winners: ColemanWinner[]): HeightBand[] {
  const pool = medallistsWithHeight(winners)
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
  const medallists = completedMedallists(bundle.winners)
  const withHeight = medallistsWithHeight(bundle.winners)
  const heights = withHeight.map((w) => w.height_cm)
  const bands = computeHeightBands(bundle.winners)

  const shortest = [...withHeight].sort((a, b) => a.height_cm - b.height_cm)[0] ?? null
  const tallest = [...withHeight].sort((a, b) => b.height_cm - a.height_cm)[0] ?? null
  const shortestColemanOnly =
    [...medallists.filter(withRecordedHeight)].sort((a, b) => a.height_cm - b.height_cm)[0] ?? null

  const mostCommonBand =
    [...bands].sort((a, b) => b.count - a.count).find((b) => b.count > 0)?.label ?? '—'

  return {
    totalMedallists: medallists.length,
    withHeight: withHeight.length,
    shortest,
    tallest,
    averageHeight: heights.length
      ? Math.round((heights.reduce((s, h) => s + h, 0) / heights.length) * 10) / 10
      : null,
    heightBands: bands,
    under180: withHeight.filter((w) => w.height_cm < 180).length,
    over195: withHeight.filter((w) => w.height_cm > 195).length,
    mostCommonBand,
    shortestColemanMedallist: shortestColemanOnly,
    royPark: bundle.winners.find((w) => w.player === 'Roy Park') ?? null,
    harryMcKay: bundle.winners.find((w) => w.player === 'Harry McKay' && w.year === 2021) ?? null,
  }
}

export function timelinePoints(
  winners: ColemanWinner[],
  challenger: ColemanChallenger,
): Array<{
  year: number
  height_cm: number
  player: string
  club: string
  goals: number
  kind: 'winner' | 'roy' | 'mckay' | 'forecast'
}> {
  const points: Array<{
    year: number
    height_cm: number
    player: string
    club: string
    goals: number
    kind: 'winner' | 'roy' | 'mckay' | 'forecast'
  }> = []

  for (const w of completedMedallists(winners)) {
    if (!withRecordedHeight(w)) continue
    let kind: 'winner' | 'roy' | 'mckay' = 'winner'
    if (w.player === 'Roy Park') kind = 'roy'
    if (w.player === 'Harry McKay' && w.year === 2021) kind = 'mckay'
    points.push({
      year: w.year,
      height_cm: w.height_cm,
      player: w.player,
      club: w.club,
      goals: w.goals,
      kind,
    })
  }

  const roy = winners.find((w) => w.player === 'Roy Park' && withRecordedHeight(w))
  if (roy && !points.some((p) => p.kind === 'roy')) {
    points.push({
      year: roy.year,
      height_cm: roy.height_cm,
      player: roy.player,
      club: roy.club,
      goals: roy.goals,
      kind: 'roy',
    })
  }

  points.push({
    year: 2026,
    height_cm: challenger.height_cm,
    player: challenger.player,
    club: challenger.club,
    goals: challenger.current_goals,
    kind: 'forecast',
  })

  return points.sort((a, b) => a.year - b.year)
}

export function generateFunFacts(stats: ColemanStats, challenger: ColemanChallenger): string[] {
  const facts: string[] = []

  if (stats.under180 != null) {
    facts.push(
      `Only ${stats.under180} Coleman Medallist${stats.under180 === 1 ? '' : 's'} on record ${stats.under180 === 1 ? 'has' : 'have'} been under 180 cm.`,
    )
  }

  if (stats.averageHeight != null) {
    facts.push(`The average Coleman Medallist is ${stats.averageHeight} cm tall (where height is recorded).`)
  }

  if (stats.tallest) {
    facts.push(
      `${stats.tallest.player} (${stats.tallest.year}) is the tallest recorded Coleman Medallist at ${stats.tallest.height_cm} cm.`,
    )
  }

  if (stats.shortestColemanMedallist) {
    facts.push(
      `${stats.shortestColemanMedallist.player} (${stats.shortestColemanMedallist.year}) is the shortest official Coleman Medallist on record at ${stats.shortestColemanMedallist.height_cm} cm.`,
    )
  }

  if (stats.royPark?.height_cm != null) {
    facts.push(
      `Roy Park ("Little Doc") led the league in 1913 at ${stats.royPark.height_cm} cm — the shortest recorded leading goalkicker in VFL/AFL history.`,
    )
  }

  if (stats.royPark?.height_cm != null && challenger.height_cm <= stats.royPark.height_cm) {
    facts.push(
      `If Nick Watson wins at ${challenger.height_cm} cm, he would match or exceed Roy Park as the shortest recorded league-leading goalkicker.`,
    )
  } else if (stats.royPark?.height_cm != null) {
    facts.push(
      `If Nick Watson wins at ${challenger.height_cm} cm, he would become the shortest Coleman Medallist since Roy Park in 1913 — more than 100 years ago.`,
    )
  }

  if (stats.over195 != null) {
    facts.push(`${stats.over195} Coleman Medallist${stats.over195 === 1 ? '' : 's'} have been taller than 195 cm.`)
  }

  facts.push(`The most common height band among winners is ${stats.mostCommonBand}.`)

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
  return [...medallistsWithHeight(winners)]
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
