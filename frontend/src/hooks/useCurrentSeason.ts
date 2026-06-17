import { useEffect, useState } from 'react'
import type { CurrentSeasonBundle } from '../types/metrics'

const base = import.meta.env.BASE_URL

export function useCurrentSeason() {
  const [data, setData] = useState<CurrentSeasonBundle | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    fetch(`${base}data/currentSeason.json`)
      .then((res) => {
        if (!res.ok) throw new Error('Current season data not found')
        return res.json()
      })
      .then((json: CurrentSeasonBundle) => {
        if (!cancelled) setData(json)
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { data, loading, error }
}
