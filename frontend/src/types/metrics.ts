export interface ClubRanking {
  club: string
  unavailableValue: number
  expectedWins: number
  actualWins: number
  delta: number
}

export interface RoundMetric {
  round: number
  value: number
  wins: number
}

export interface UnavailablePlayer {
  player: string
  club: string
  roundsMissed: number
  pvs: number
  status: 'unavailable' | 'vfl_only' | 'intermittent'
}

export interface ContinuityMetric {
  archetype: string
  changes: number
  score: number
}

export interface MockMetrics {
  meta: { season: number; round: number; generatedAt: string; note: string }
  leagueOverview: {
    avgUnavailableValue: number
    clubsAboveExpectation: number
    clubsBelowExpectation: number
    topUnavailableClub: string
    correlationUnavailableToWins: number
  }
  clubUnavailableByRound: RoundMetric[]
  clubRankings: ClubRanking[]
  topUnavailablePlayers: UnavailablePlayer[]
  continuity: ContinuityMetric[]
  regression: {
    model: string
    rSquared: number
    coefficients: Record<string, number>
    interpretation: string
  }
}
