import { useEffect, useState } from 'react'
import type { ColemanHeightsBundle } from '../types/coleman'

const base = import.meta.env.BASE_URL

export function useColemanHeights() {
  const [data, setData] = useState<ColemanHeightsBundle | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    fetch(`${base}data/colemanWinnersHeights.json`)
      .then((res) => {
        if (!res.ok) throw new Error('Coleman heights data not found')
        return res.json()
      })
      .then((json: ColemanHeightsBundle) => {
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
