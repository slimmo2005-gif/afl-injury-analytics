import { CHART_MAX_SEASON, LADDER_SIZE, MIN_SEASON } from '../constants'
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

/** Only claim clear over/underperformance above this many ladder places. */
export const SIGNIFICANT_DELTA = 4

const HARDEST_HIT_THRESHOLD = LADDER_SIZE - 2 // pvsLostRank >= 16
const HEALTHIEST_THRESHOLD = 3 // pvsLostRank <= 3

const CLUB_SHORT: Record<string, string> = {
  'Brisbane Lions': 'Lions',
  'Gold Coast': 'Suns',
  'Greater Western Sydney': 'Giants',
  'North Melbourne': 'Kangaroos',
  'Port Adelaide': 'Power',
  'St Kilda': 'Saints',
  'West Coast': 'Eagles',
  'Western Bulldogs': 'Bulldogs',
  Geelong: 'Cats',
  Essendon: 'Bombers',
  Collingwood: 'Magpies',
  Hawthorn: 'Hawks',
  Melbourne: 'Demons',
  Richmond: 'Tigers',
  Sydney: 'Swans',
  Adelaide: 'Crows',
  Carlton: 'Blues',
  Fremantle: 'Dockers',
}

function clubLabel(club: string): string {
  return CLUB_SHORT[club] ?? club
}

function ordinal(n: number): string {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return s[(v - 20) % 10] || s[v] || s[0]
}

function ladderPhrase(rank: number): string {
  return `${rank}${ordinal(rank)}`
}

function isSignificantOverperform(rankDelta: number): boolean {
  return rankDelta <= -(SIGNIFICANT_DELTA + 1)
}

function isSignificantUnderperform(rankDelta: number): boolean {
  return rankDelta >= SIGNIFICANT_DELTA + 1
}

/**
 * Classify rank delta for tables and styling.
 * Negative delta = outperformed injury profile; positive = underperformed.
 */
export function getDeltaCategory(rankDelta: number): DeltaCategory {
  if (rankDelta <= -5) return 'massive_outperformer'
  if (rankDelta <= -3) return 'outperformed'
  if (rankDelta >= 5) return 'major_underperformer'
  if (rankDelta >= 3) return 'underperformed'
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
      return 'Matched expectation'
    case 'underperformed':
      return 'Underperformed injury profile'
    case 'major_underperformer':
      return 'Major underperformer'
  }
}

/** Display label for injury-impact rank (1 = healthiest). */
export function formatInjuryRank(pvsLostRank: number): string {
  if (pvsLostRank === 1) return 'Healthiest (#1)'
  if (pvsLostRank === LADDER_SIZE) return 'Hardest hit (#18)'
  return `#${pvsLostRank}`
}

/** Short label for the ladder-vs-injuries metric card. */
export function getDeltaLabel(rankDelta: number): string {
  const abs = Math.abs(rankDelta)
  if (abs <= SIGNIFICANT_DELTA) return 'Matched expectation'
  if (rankDelta > 0) return 'Underperformed'
  return 'Outperformed'
}

export function getDeltaSubtitle(rankDelta: number): string {
  const abs = Math.abs(rankDelta)
  if (abs <= SIGNIFICANT_DELTA) return 'Ladder finish matched injury profile'
  if (rankDelta > 0) return `Finished ${abs} place${abs === 1 ? '' : 's'} lower than injury profile suggested`
  return `Finished ${abs} place${abs === 1 ? '' : 's'} higher than injury profile suggested`
}

/** One-word outcome label for ladder vs injury rank delta. */
export function rankDeltaPerformanceLabel(rankDelta: number): string {
  const abs = Math.abs(rankDelta)
  if (abs <= SIGNIFICANT_DELTA) return 'Matched expectation'
  if (rankDelta > 0) return 'Underperformed'
  return 'Outperformed'
}

export function getDeltaAccent(rankDelta: number): StoryAccent {
  if (isSignificantOverperform(rankDelta)) return 'positive'
  if (isSignificantUnderperform(rankDelta)) return 'warning'
  return 'neutral'
}

/**
 * Hero headline — strong language when |rankDelta| > 4; calls out extreme mismatches.
 * @param worstPositiveDeltaInDataset max rank_delta in 2021–2025 (or current window) for context
 * @param worstNegativeDeltaInDataset min (most negative) rank_delta in the window
 */
export function generateHeadline(
  data: ClubSeasonStoryData,
  worstPositiveDeltaInDataset?: number,
  worstNegativeDeltaInDataset?: number,
): string {
  const { club, ladderRank, pvsLostRank, rankDelta } = data
  const absDelta = Math.abs(rankDelta)
  const label = clubLabel(club)
  const hardestInLeague = pvsLostRank === LADDER_SIZE
  const healthiestInLeague = pvsLostRank === 1
  const isDatasetWorstUnder =
    worstPositiveDeltaInDataset != null &&
    rankDelta > 0 &&
    rankDelta >= worstPositiveDeltaInDataset
  const isDatasetBestOver =
    worstNegativeDeltaInDataset != null &&
    rankDelta < 0 &&
    rankDelta <= worstNegativeDeltaInDataset

  if (isSignificantOverperform(rankDelta)) {
    if (pvsLostRank >= HARDEST_HIT_THRESHOLD) {
      return `${club} overcame one of the league's heaviest injury tolls to finish ${ladderPhrase(ladderRank)}.`
    }
    if (isDatasetBestOver) {
      return `${club} finished ${ladderPhrase(ladderRank)} despite ranking #${pvsLostRank} for injury impact — the largest overperformance vs unavailability in our 2021–2025 data.`
    }
    if (absDelta >= 10) {
      return `${club} finished ${ladderPhrase(ladderRank)} despite ranking #${pvsLostRank} for injury impact — a massive overachiever.`
    }
    return `${club} finished ${absDelta} places above where their injury profile suggested.`
  }

  if (isSignificantUnderperform(rankDelta)) {
    // Healthiest (or near-healthiest) list but a poor ladder finish — call it out plainly.
    if (healthiestInLeague && rankDelta >= 10) {
      if (isDatasetWorstUnder) {
        return `${club} finished ${ladderPhrase(ladderRank)} despite the AFL's best injury luck — the largest underperformance vs unavailability in our 2021–2025 data.`
      }
      return `${club} finished ${ladderPhrase(ladderRank)} despite the league's best injury luck — a massive outlier season.`
    }
    if (pvsLostRank <= 2 && rankDelta >= 10) {
      return `${club} crashed to ${ladderPhrase(ladderRank)} despite top-tier injury luck (rank #${pvsLostRank} for unavailability).`
    }
    if (pvsLostRank <= HEALTHIEST_THRESHOLD) {
      if (isDatasetWorstUnder) {
        return `${club}'s healthy list did not translate — they finished ${absDelta} places below expectation, the worst gap in our 2021–2025 data.`
      }
      return `${club} had one of the league's healthiest lists but still finished ${ladderPhrase(ladderRank)} — ${absDelta} places below where unavailability suggested.`
    }
    if (pvsLostRank >= HARDEST_HIT_THRESHOLD) {
      return `${club}'s heavy injury toll aligns with a ${ladderPhrase(ladderRank)} finish.`
    }
    return `${club} finished ${absDelta} places lower than their injury profile suggested.`
  }

  // Moderate delta (±4 or less): lead with injury facts, not over/under claims.
  if (healthiestInLeague) {
    return `The ${label} had the least injury impact of any team, finishing ${ladderPhrase(ladderRank)}.`
  }
  if (hardestInLeague) {
    if (ladderRank >= 15) {
      return `${club}'s injury toll was the heaviest in the league, keeping them near the bottom at ${ladderPhrase(ladderRank)}.`
    }
    return `${club}'s injury toll was the heaviest in the league, finishing ${ladderPhrase(ladderRank)}.`
  }
  if (pvsLostRank <= HEALTHIEST_THRESHOLD) {
    return `${club} had one of the league's healthiest lists, finishing ${ladderPhrase(ladderRank)}.`
  }
  if (pvsLostRank >= HARDEST_HIT_THRESHOLD) {
    return `${club} battled one of the league's worst injury tolls, finishing ${ladderPhrase(ladderRank)}.`
  }

  return `${club}'s ladder finish (${ladderPhrase(ladderRank)}) matched expectation for its injury profile.`
}

/**
 * Optional second line when this season is a club high/low for unavailability PVS.
 * Only compares seasons from MIN_SEASON onward (reliable data window).
 */
export function generateSubheadline(
  data: ClubSeasonStoryData,
  clubHistory: LadderPvsSeasonRank[],
  worstPositiveDeltaInDataset?: number,
  worstNegativeDeltaInDataset?: number,
): string | null {
  if (
    worstPositiveDeltaInDataset != null &&
    data.rankDelta > 0 &&
    data.rankDelta >= worstPositiveDeltaInDataset
  ) {
    return `This is the largest gap between injury luck and ladder finish in our 2021–2025 dataset (+${data.rankDelta} rank delta).`
  }

  if (
    worstNegativeDeltaInDataset != null &&
    data.rankDelta < 0 &&
    data.rankDelta <= worstNegativeDeltaInDataset &&
    data.pvsLostRank < HARDEST_HIT_THRESHOLD
  ) {
    return `This is the largest overperformance vs unavailability in our 2021–2025 dataset (${data.rankDelta} rank delta).`
  }

  const reliable = clubHistory.filter((h) => h.season >= MIN_SEASON)
  if (reliable.length < 2) return null

  const pvsValues = reliable.map((h) => h.pvsLost)
  const maxPvs = Math.max(...pvsValues)
  const minPvs = Math.min(...pvsValues)

  if (data.seasonUnavailablePvs >= maxPvs - 0.05) {
    return `This was ${data.club}'s heaviest injury-impact season in the dataset.`
  }
  if (data.seasonUnavailablePvs <= minPvs + 0.05) {
    return `This was ${data.club}'s lightest injury-impact season in the dataset.`
  }
  return null
}

/** 2–3 sentence conversational summary; avoids claiming injuries caused outcomes. */
export function generateClubSeasonSummary(data: ClubSeasonStoryData): string {
  const { club, season, ladderRank, pvsLostRank, rankDelta, seasonUnavailablePvs, wins } =
    data
  const absDelta = Math.abs(rankDelta)
  const injuryDesc =
    pvsLostRank === LADDER_SIZE
      ? 'the heaviest injury toll in the league'
      : pvsLostRank === 1
        ? 'the lightest injury toll in the league'
        : pvsLostRank >= HARDEST_HIT_THRESHOLD
          ? 'one of the harder-hit lists in the league'
          : pvsLostRank <= HEALTHIEST_THRESHOLD
            ? 'one of the healthier lists by PVS lost'
            : 'a mid-range injury profile'

  let para1: string
  if (absDelta <= SIGNIFICANT_DELTA) {
    para1 = `${club}'s ${season} season saw a ${ladderPhrase(ladderRank)} finish with an injury-impact rank of ${pvsLostRank} (${injuryDesc}) — matched expectation.`
  } else if (isSignificantOverperform(rankDelta)) {
    para1 = `${club}'s ${season} season stands out: they finished ${absDelta} places higher on the ladder than their injury toll suggested, ending ${ladderPhrase(ladderRank)} despite ranking ${pvsLostRank} for injury impact (${injuryDesc}).`
  } else if (isSignificantUnderperform(rankDelta)) {
    para1 = `${club}'s ${season} finish (${ladderPhrase(ladderRank)}) landed ${absDelta} places lower than their injury-impact rank of ${pvsLostRank} suggested — ${injuryDesc}.`
  }

  let para2: string
  if (isSignificantOverperform(rankDelta)) {
    para2 =
      'That gap may indicate strong depth or available players outperforming their baseline — not that injuries were irrelevant.'
  } else if (isSignificantUnderperform(rankDelta)) {
    if (pvsLostRank <= HEALTHIEST_THRESHOLD) {
      para2 =
        'Injuries are unlikely to fully explain that ladder finish — form, list quality, coaching, or other factors may have mattered more.'
    } else {
      para2 =
        'That pattern is consistent with injuries weighing on results, though form, fixture, and list quality also matter.'
    }
  } else {
    para2 = `With ${wins} wins and ${seasonUnavailablePvs.toFixed(0)} PVS lost to injury-listed absences, the season story fits a moderate injury–ladder relationship.`
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
      subtitle: 'Total PVS lost (injury absences only)',
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
      mainValue: formatInjuryRank(data.pvsLostRank),
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
  const { club, season, rankDelta, pvsLostRank, ladderRank } = data
  const absDelta = Math.abs(rankDelta)

  const headlines: string[] = []

  if (pvsLostRank === 1) {
    headlines.push(
      `${club} had the AFL's lightest injury toll in ${season} — they finished ${ladderPhrase(ladderRank)}`,
    )
  } else if (absDelta <= SIGNIFICANT_DELTA) {
    headlines.push(`${club}'s ${season} ladder finish matched expectation for its injury profile`)
  } else if (isSignificantOverperform(rankDelta)) {
    headlines.push(
      `${club} ${season}: finished ${absDelta} places above where injuries suggested`,
    )
  } else {
    headlines.push(
      `${club} ${season}: finished ${absDelta} places below where injuries suggested`,
    )
  }

  headlines.push('The AFL Injury Luck Ladder: who outperformed despite injuries?')
  headlines.push(`Which clubs were actually hurt most by injuries in ${season}?`)

  if (pvsLostRank === LADDER_SIZE) {
    headlines[2] = `${club} carried the heaviest injury toll in ${season} — did it show on the ladder?`
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
  const outcome = rankDeltaPerformanceLabel(rankDelta)
  if (absDelta <= SIGNIFICANT_DELTA) {
    return `${club} finished ${ladderPhrase(ladderRank)} with injury-impact rank ${pvsLostRank} — ${outcome}.`
  }
  if (rankDelta > 0) {
    return `${club} finished ${ladderPhrase(ladderRank)} with injury-impact rank ${pvsLostRank} — ${outcome} (${rankDelta} places).`
  }
  return `${club} finished ${ladderPhrase(ladderRank)} with injury-impact rank ${pvsLostRank} — ${outcome} (${absDelta} places).`
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
    // Prefer ladder bundle PVS (injury absences only) over round-chart totals.
    seasonUnavailablePvs: rank.pvsLost || seasonUnavailablePvs,
    top5UnavailablePvs,
  }
}

/** Max positive rank delta across club-seasons in the reliable window (2021+). */
export function maxPositiveRankDelta(
  byClub: Record<string, LadderPvsSeasonRank[]> | undefined,
  maxSeason: number = CHART_MAX_SEASON,
): number {
  if (!byClub) return 0
  let max = 0
  for (const history of Object.values(byClub)) {
    for (const row of history) {
      if (row.season >= MIN_SEASON && row.season <= maxSeason && row.rankDelta > max) {
        max = row.rankDelta
      }
    }
  }
  return max
}

/** Min (most negative) rank delta across club-seasons in the reliable window (2021+). */
export function minNegativeRankDelta(
  byClub: Record<string, LadderPvsSeasonRank[]> | undefined,
  maxSeason: number = CHART_MAX_SEASON,
): number {
  if (!byClub) return 0
  let min = 0
  for (const history of Object.values(byClub)) {
    for (const row of history) {
      if (row.season >= MIN_SEASON && row.season <= maxSeason && row.rankDelta < min) {
        min = row.rankDelta
      }
    }
  }
  return min
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
