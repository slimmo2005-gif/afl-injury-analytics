import type { MockMetrics, UnavailablePlayer } from '../types/metrics'

/** Top unavailable players for a club in a season (up to 5). */
export function getClubTopUnavailablePlayers(
  data: Pick<MockMetrics, 'seasons' | 'topUnavailablePlayers'>,
  club: string,
  season: number,
): UnavailablePlayer[] {
  const seasonBundle = data.seasons?.[String(season)]
  const fromClubMap = seasonBundle?.topUnavailableByClub?.[club]
  if (fromClubMap?.length) return fromClubMap

  return (seasonBundle?.topUnavailablePlayers ?? data.topUnavailablePlayers)
    .filter((p) => p.club === club)
    .slice(0, 5)
}
