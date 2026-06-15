import { LADDER_SIZE } from '../constants'
import type { LadderPvsSeasonRank } from '../types/metrics'

/** Inputs for narrative helpers on a single club/season. */
export interface ClubSeasonStoryData {
  club: string
  season: number
  wins: number
  ladderRank: number
  /** Rank by fewest PVS lost: 1 = healthiest list, 18 = hardest hit. */
  pvsLostRank: number
  /** ladderRank − pvsLostRank; positive = finished lower than injury profile suggests. */
  rankDelta: number
  seasonUnavailablePvs: number
  top5UnavailablePvs: number
}

export type DeltaCategory =
  | 'massive_outperformer'
  | 'outperformed'
  | 'matched'
  | 'underperformed'
  | 'major_underperformer'

export type StoryAccent = 'positive' | 'neutral' | 'warning'

export interface MetricCardContent {
  title: string
  mainValue: string
  subtitle: string
  accent: StoryAccent
}

const HARDEST_HIT_THRESHOLD = LADDER_SIZE - 2 // pvsLostRank >= 16
const HEALTHIEST_THRESHOLD = 3 // pvsLostRank <= 3

/**
 * Classify rank delta for tables and styling.
 * Negative delta = outperformed injury profile; positive = underperformed.
 */
export function getDeltaCategory(rankDelta: number): DeltaCategory {
  if (rankDelta <= -4) return 'massive_outperformer'
  if (rankDelta <= -2) return 'outperformed'
  if (rankDelta >= 4) return 'major_underperformer'
  if (rankDelta >= 2) return 'underperformed'
  return 'matched'
}

/** Plain-English interpretation label for league tables. */
export function getDeltaInterpretation(rankDelta: number): string {
  const cat = getDeltaCategory(rankDelta)
  switch (cat) {
    case 'massive_outperformer':
      return 'Massive outperformer'
    case 'outperformed':
      return 'Outperformed injury profile'
    case 'matched':
      return 'Matched injury profile'
    case 'underperformed':
      return 'Underperformed injury profile'
    case 'major_underperformer':
      return 'Major underperformer'
  }
}

/** Short label for the ladder-vs-injuries metric card. */
export function getDeltaLabel(rankDelta: number): string {
  if (rankDelta > 0) return `+${rankDelta} places`
  if (rankDelta < 0) return `${rankDelta} places`
  return 'Matched'
}

export function getDeltaSubtitle(rankDelta: number): string {
  if (rankDelta > 0) return 'Finished lower than injury profile suggested'
  if (rankDelta < 0) return 'Finished higher than injury profile suggested'
  return 'Finished exactly as injury profile suggested'
}

export function getDeltaAccent(rankDelta: number): StoryAccent {
  if (rankDelta <= -2) return 'positive'
  if (rankDelta >= 2) return 'warning'
  return 'neutral'
}

function injuryTollQualifier(pvsLostRank: number): string | null {
  if (pvsLostRank >= HARDEST_HIT_THRESHOLD) {
    return 'one of the AFL\'s worst injury tolls'
  }
  if (pvsLostRank <= HEALTHIEST_THRESHOLD) {
    return 'one of the AFL\'s healthiest lists'
  }
  return null
}

/**
 * Hero headline answering “Did injuries explain this club’s season?”
 * Uses rank delta; appends injury-toll context when extreme.
 */
export function generateHeadline(data: ClubSeasonStoryData): string {
  const { club, rankDelta, pvsLostRank } = data
  const absDelta = Math.abs(rankDelta)
  let base: string

  if (absDelta <= 1) {
    base = `${club} finished almost exactly where its injury profile suggested.`
  } else if (rankDelta >= 2) {
    base = `${club} finished ${rankDelta} places lower than its injury profile suggested.`
  } else {
    base = `${club} finished ${absDelta} places higher than its injury profile suggested.`
  }

  const qualifier = injuryTollQualifier(pvsLostRank)
  if (!qualifier) return base

  if (rankDelta <= -2) {
    return `${club} overcame ${qualifier}.`
  }
  if (absDelta <= 1) {
    return `${club} stayed near expectation despite ${qualifier === 'one of the AFL\'s healthiest lists' ? 'a healthy list' : 'a moderate injury toll'}.`
  }
  if (qualifier === 'one of the AFL\'s worst injury tolls' && rankDelta >= 2) {
    return `${club} finished ${rankDelta} places lower — consistent with ${qualifier}.`
  }
  return `${base} They had ${qualifier}.`
}

/**
 * Optional second line when this season is a club high/low for unavailability PVS.
 */
export function generateSubheadline(
  data: ClubSeasonStoryData,
  clubHistory: LadderPvsSeasonRank[],
): string | null {
  if (clubHistory.length < 2) return null

  const pvsValues = clubHistory.map((h) => h.pvsLost)
  const maxPvs = Math.max(...pvsValues)
  const minPvs = Math.min(...pvsValues)

  if (data.seasonUnavailablePvs >= maxPvs - 0.05) {
    return `This was ${data.club}'s worst unavailability season in the dataset.`
  }
  if (data.seasonUnavailablePvs <= minPvs + 0.05) {
    return `This was ${data.club}'s healthiest season in the dataset.`
  }
  return null
}

/** 2–3 sentence conversational summary; avoids claiming injuries caused outcomes. */
export function generateClubSeasonSummary(data: ClubSeasonStoryData): string {
  const {
    club,
    season,
    ladderRank,
    pvsLostRank,
    rankDelta,
    seasonUnavailablePvs,
    wins,
  } = data
  const absDelta = Math.abs(rankDelta)
  const injuryDesc =
    pvsLostRank >= HARDEST_HIT_THRESHOLD
      ? 'one of the hardest-hit lists in the league'
      : pvsLostRank <= HEALTHIEST_THRESHOLD
        ? 'a relatively healthy list by PVS lost'
        : 'a mid-range injury profile'

  let para1: string
  if (absDelta <= 1) {
    para1 = `${club}'s ${season} ladder position closely tracked its injury-impact profile. The club finished ${ladderRank}${ordinal(ladderRank)} with an injury-impact rank of ${pvsLostRank} (${injuryDesc}).`
  } else if (rankDelta <= -2) {
    para1 = `${club}'s ${season} season stands out because they finished ${absDelta} places higher on the ladder than their injury toll suggested. They ended ${ladderRank}${ordinal(ladderRank)} despite ranking ${pvsLostRank} for injury impact — ${injuryDesc}.`
  } else {
    para1 = `${club}'s ${season} finish (${ladderRank}${ordinal(ladderRank)} on the ladder) was ${absDelta} places lower than their injury-impact rank of ${pvsLostRank} suggested — ${injuryDesc}.`
  }

  let para2: string
  if (rankDelta <= -2) {
    para2 =
      'That pattern may indicate strong depth, good coaching, or that available players outperformed their baseline value — not that injuries were irrelevant.'
  } else if (rankDelta >= 2) {
    para2 =
      'That gap is consistent with injuries weighing on results, though form, fixture, and list quality also shape where a club lands.'
  } else {
    para2 = `With ${wins} wins and ${seasonUnavailablePvs.toFixed(0)} total PVS lost, their season story aligns with what the injury model would expect.`
  }

  return `${para1} ${para2}`
}

/** Four story cards for the club page hero metrics row. */
export function getMetricCardContent(data: ClubSeasonStoryData): MetricCardContent[] {
  const pvs =
    data.seasonUnavailablePvs >= 100
      ? data.seasonUnavailablePvs.toFixed(0)
      : data.seasonUnavailablePvs.toFixed(1)

  return [
    {
      title: 'Injury impact',
      mainValue: pvs,
      subtitle: 'Total PVS lost',
      accent: 'neutral',
    },
    {
      title: 'Worst absences',
      mainValue:
        data.top5UnavailablePvs >= 100
          ? data.top5UnavailablePvs.toFixed(0)
          : data.top5UnavailablePvs.toFixed(1),
      subtitle: 'PVS lost from top 5 unavailable players',
      accent: 'neutral',
    },
    {
      title: 'Injury rank',
      mainValue: `#${data.pvsLostRank}`,
      subtitle: '1 = healthiest · 18 = hardest hit',
      accent:
        data.pvsLostRank >= HARDEST_HIT_THRESHOLD
          ? 'warning'
          : data.pvsLostRank <= HEALTHIEST_THRESHOLD
            ? 'positive'
            : 'neutral',
    },
    {
      title: 'Ladder vs injuries',
      mainValue: getDeltaLabel(data.rankDelta),
      subtitle: getDeltaSubtitle(data.rankDelta),
      accent: getDeltaAccent(data.rankDelta),
    },
  ]
}

/** Three share-friendly headlines for Reddit/X. */
export function generateShareHeadlines(data: ClubSeasonStoryData): string[] {
  const { club, season, rankDelta, pvsLostRank } = data
  const absDelta = Math.abs(rankDelta)

  const headlines: string[] = []

  if (absDelta <= 1) {
    headlines.push(
      `${club}'s ${season} ladder finish almost perfectly matched its injury profile`,
    )
  } else if (rankDelta <= -2) {
    headlines.push(
      `${club} ${season}: finished ${absDelta} places above where injuries suggested`,
    )
  } else {
    headlines.push(
      `${club} ${season}: injuries may explain finishing ${absDelta} places below expectation`,
    )
  }

  headlines.push('The AFL Injury Luck Ladder: who overachieved despite injuries?')
  headlines.push(`Which clubs were actually hurt most by injuries in ${season}?`)

  if (pvsLostRank >= HARDEST_HIT_THRESHOLD) {
    headlines[2] = `${club} had one of the AFL's worst injury tolls in ${season} — did it show on the ladder?`
  }

  return headlines.slice(0, 3)
}

/** Tooltip sentence for the ladder vs injury chart at a point in time. */
export function chartTooltipNarrative(
  club: string,
  ladderRank: number,
  pvsLostRank: number,
  rankDelta: number,
): string {
  const absDelta = Math.abs(rankDelta)
  if (absDelta <= 1) {
    return `${club} finished ${ladderRank}${ordinal(ladderRank)} and ranked ${pvsLostRank} for injury impact — closely matched.`
  }
  if (rankDelta > 0) {
    return `${club} finished ${ladderRank}${ordinal(ladderRank)} and ranked ${pvsLostRank} for injury impact, meaning they finished ${rankDelta} places lower than expected from their injury profile.`
  }
  return `${club} finished ${ladderRank}${ordinal(ladderRank)} and ranked ${pvsLostRank} for injury impact, meaning they finished ${absDelta} places higher than expected from their injury profile.`
}

function ordinal(n: number): string {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return s[(v - 20) % 10] || s[v] || s[0]
}

/** Build story data from ladder rank row + club ranking totals. */
export function buildClubSeasonStoryData(
  club: string,
  season: number,
  rank: LadderPvsSeasonRank,
  seasonUnavailablePvs: number,
  top5UnavailablePvs: number,
): ClubSeasonStoryData {
  return {
    club,
    season,
    wins: rank.wins,
    ladderRank: rank.ladderRank,
    pvsLostRank: rank.pvsLostRank,
    rankDelta: rank.rankDelta,
    seasonUnavailablePvs: seasonUnavailablePvs || rank.pvsLost,
    top5UnavailablePvs,
  }
}

/** Simple linear regression R² for model-fit scatter (x = injury rank, y = ladder rank). */
export function computeRankCorrelationR2(
  points: { pvsLostRank: number; ladderRank: number }[],
): number | null {
  if (points.length < 3) return null
  const xs = points.map((p) => p.pvsLostRank)
  const ys = points.map((p) => p.ladderRank)
  const n = xs.length
  const meanX = xs.reduce((a, b) => a + b, 0) / n
  const meanY = ys.reduce((a, b) => a + b, 0) / n

  let ssXX = 0
  let ssXY = 0
  for (let i = 0; i < n; i++) {
    ssXX += (xs[i] - meanX) ** 2
    ssXY += (xs[i] - meanX) * (ys[i] - meanY)
  }
  if (ssXX === 0) return null

  const slope = ssXY / ssXX
  const intercept = meanY - slope * meanX

  let ssRes = 0
  let ssTot = 0
  for (let i = 0; i < n; i++) {
    const pred = intercept + slope * xs[i]
    ssRes += (ys[i] - pred) ** 2
    ssTot += (ys[i] - meanY) ** 2
  }
  if (ssTot === 0) return null
  return Math.max(0, Math.min(1, 1 - ssRes / ssTot))
}
