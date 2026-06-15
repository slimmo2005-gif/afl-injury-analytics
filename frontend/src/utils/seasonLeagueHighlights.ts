import type { LadderPvsSeasonRank } from '../types/metrics'

export interface SeasonHighlightClub {
  club: string
  rankDelta: number
  pvsLostRank: number
  ladderRank: number
}

export interface SeasonLeagueHighlights {
  season: number
  biggestOverachiever: SeasonHighlightClub | null
  hardestHit: SeasonHighlightClub | null
  luckiestClub: SeasonHighlightClub | null
}

function seasonRows(
  season: number,
  byClub: Record<string, LadderPvsSeasonRank[]> | undefined,
): SeasonHighlightClub[] {
  if (!byClub) return []
  const rows: SeasonHighlightClub[] = []
  for (const [club, history] of Object.entries(byClub)) {
    const row = history.find((h) => h.season === season)
    if (row) {
      rows.push({
        club,
        rankDelta: row.rankDelta,
        pvsLostRank: row.pvsLostRank,
        ladderRank: row.ladderRank,
      })
    }
  }
  return rows
}

/** League-wide standouts for a single season (injury rank vs ladder). */
export function computeSeasonLeagueHighlights(
  season: number,
  byClub: Record<string, LadderPvsSeasonRank[]> | undefined,
): SeasonLeagueHighlights {
  const rows = seasonRows(season, byClub)
  if (!rows.length) {
    return { season, biggestOverachiever: null, hardestHit: null, luckiestClub: null }
  }

  const biggestOverachiever = [...rows].sort(
    (a, b) => a.rankDelta - b.rankDelta || a.club.localeCompare(b.club),
  )[0]

  const hardestHit = [...rows].sort(
    (a, b) =>
      b.pvsLostRank - a.pvsLostRank ||
      b.rankDelta - a.rankDelta ||
      a.club.localeCompare(b.club),
  )[0]

  const luckiestClub = [...rows].sort(
    (a, b) =>
      a.pvsLostRank - b.pvsLostRank ||
      a.rankDelta - b.rankDelta ||
      a.club.localeCompare(b.club),
  )[0]

  return {
    season,
    biggestOverachiever: biggestOverachiever.rankDelta < 0 ? biggestOverachiever : null,
    hardestHit,
    luckiestClub,
  }
}

/** Casual-fan label for overperformance magnitude. */
export function formatOverachieverPlaces(rankDelta: number): string {
  const places = Math.abs(rankDelta)
  return `+${places} ladder place${places === 1 ? '' : 's'}`
}
