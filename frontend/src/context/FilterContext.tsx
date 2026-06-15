import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { DEFAULT_SEASON, MIN_SEASON } from '../constants'
import { useMetricsContext } from './MetricsContext'

export interface Filters {
  season: number
  club: string
}

const FilterContext = createContext<{
  filters: Filters
  setSeason: (s: number) => void
  setClub: (c: string) => void
} | null>(null)

export function FilterProvider({ children }: { children: ReactNode }) {
  const { data } = useMetricsContext()
  const defaultSeason = data.meta.defaultSeason ?? data.meta.season ?? DEFAULT_SEASON
  const defaultClub =
    data.defaultClub ?? data.clubRankings[0]?.club ?? 'Collingwood'

  const [season, setSeason] = useState(defaultSeason)
  const [club, setClub] = useState(defaultClub)

  useEffect(() => {
    const key = String(season)
    const clubsForSeason =
      data.seasons?.[key]?.clubs ?? data.clubs ?? data.clubRankings.map((c) => c.club)
    if (clubsForSeason.length && !clubsForSeason.includes(club)) {
      setClub(clubsForSeason[0])
    }
  }, [season, data, club])

  const value = useMemo(
    () => ({ filters: { season, club }, setSeason, setClub }),
    [season, club],
  )

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>
}

export function useFilters() {
  const ctx = useContext(FilterContext)
  if (!ctx) throw new Error('useFilters must be used within FilterProvider')
  return ctx
}

export function useSeasonOptions(): number[] {
  const { data } = useMetricsContext()
  const seasons = data.meta.seasons ?? [data.meta.season]
  return [...seasons].filter((s) => s >= MIN_SEASON).sort((a, b) => b - a)
}
