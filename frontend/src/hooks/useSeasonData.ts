import { useMemo } from 'react'
import { useFilters } from '../context/FilterContext'
import { useMetricsContext } from '../context/MetricsContext'
import type { MockMetrics } from '../types/metrics'

/** Resolve season-specific slice from multi-season metrics bundle. */
export function useSeasonData(): MockMetrics & { clubs: string[]; defaultClub: string } {
  const { data } = useMetricsContext()
  const { filters } = useFilters()

  return useMemo(() => {
    const key = String(filters.season)
    const seasonData = data.seasons?.[key]
    if (seasonData) {
      return {
        ...data,
        ...seasonData,
        meta: { ...data.meta, season: filters.season },
        clubs: seasonData.clubs ?? seasonData.clubRankings.map((c) => c.club),
        defaultClub: seasonData.defaultClub ?? filters.club,
        clubSeries: seasonData.clubSeries,
      }
    }
    return {
      ...data,
      clubs: data.clubRankings.map((c) => c.club),
      defaultClub: data.defaultClub ?? filters.club,
    }
  }, [data, filters.season, filters.club])
}
