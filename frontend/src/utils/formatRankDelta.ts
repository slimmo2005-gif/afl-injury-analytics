/** Ladder rank − PVS-lost rank; positive = finished lower than injury toll suggests. */
export function formatRankDelta(delta: number): string {
  if (delta > 0) return `+${delta}`
  if (delta < 0) return `${delta}`
  return '0'
}

export const RANK_DELTA_DOMAIN: [number, number] = [-17, 17]
