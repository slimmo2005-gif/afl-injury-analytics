import { createContext, useContext, type ReactNode } from 'react'
import { useMetrics } from '../hooks/useMetrics'
import type { MockMetrics } from '../types/metrics'

type MetricsContextValue = ReturnType<typeof useMetrics>

const MetricsContext = createContext<MetricsContextValue | null>(null)

export function MetricsProvider({ children }: { children: ReactNode }) {
  const value = useMetrics()
  return <MetricsContext.Provider value={value}>{children}</MetricsContext.Provider>
}

export function useMetricsContext(): MetricsContextValue {
  const ctx = useContext(MetricsContext)
  if (!ctx) throw new Error('useMetricsContext must be used within MetricsProvider')
  return ctx
}

export type { MockMetrics }
