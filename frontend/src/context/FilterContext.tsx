import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useMetricsContext } from './MetricsContext'

export interface Filters {
  season: number
  club: string
  ageCohort: 'all' | 'u22' | '22-27' | '28+'
}

const FilterContext = createContext<{
  filters: Filters
  setSeason: (s: number) => void
  setClub: (c: string) => void
  setAgeCohort: (a: Filters['ageCohort']) => void
} | null>(null)

export function FilterProvider({ children }: { children: ReactNode }) {
  const { data } = useMetricsContext()
  const defaultSeason = data.meta.defaultSeason ?? data.meta.season
  const defaultClub =
    data.defaultClub ??
    data.clubRankings[0]?.club ??
    'Collingwood'

  const [season, setSeason] = useState(defaultSeason)
  const [club, setClub] = useState(defaultClub)
  const [ageCohort, setAgeCohort] = useState<Filters['ageCohort']>('all')

  useEffect(() => {
    const key = String(season)
    const clubsForSeason =
      data.seasons?.[key]?.clubs ?? data.clubs ?? data.clubRankings.map((c) => c.club)
    if (clubsForSeason.length && !clubsForSeason.includes(club)) {
      setClub(clubsForSeason[0])
    }
  }, [season, data, club])

  const value = useMemo(
    () => ({ filters: { season, club, ageCohort }, setSeason, setClub, setAgeCohort }),
    [season, club, ageCohort],
  )

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>
}

export function useFilters() {
  const ctx = useContext(FilterContext)
  if (!ctx) throw new Error('useFilters must be used within FilterProvider')
  return ctx
}
