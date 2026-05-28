import { useEffect, useState } from 'react'
import mock from '../data/mockMetrics.json'
import type { MockMetrics } from '../types/metrics'

const base = import.meta.env.BASE_URL

export function useMetrics() {
  const [data, setData] = useState<MockMetrics>(mock as MockMetrics)
  const [loading, setLoading] = useState(true)
  const [source, setSource] = useState<'mock' | 'live'>('mock')

  useEffect(() => {
    let cancelled = false
    fetch(`${base}data/metrics.json`)
      .then((res) => {
        if (!res.ok) throw new Error('metrics not found')
        return res.json()
      })
      .then((json: MockMetrics) => {
        if (!cancelled) {
          setData(json)
          setSource('live')
        }
      })
      .catch(() => {
        if (!cancelled) setSource('mock')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { data, loading, source }
}
