export interface ClubRanking {
  club: string
  unavailableValue: number
  unavailableTop5?: number
  expectedWins: number
  actualWins: number
  delta: number
}

export interface RoundMetric {
  round: number
  value: number
  top5?: number
  wins: number
}

export interface UnavailablePlayer {
  player: string
  club: string
  roundsMissed: number
  pvs: number
  unavailablePvs?: number
  status: 'unavailable' | 'vfl_only' | 'intermittent'
}

export interface ContinuityMetric {
  archetype: string
  changes: number
  score: number
}

export interface SeasonBundle {
  leagueOverview: MockMetrics['leagueOverview']
  clubUnavailableByRound: RoundMetric[]
  clubRankings: ClubRanking[]
  topUnavailablePlayers: UnavailablePlayer[]
  continuity: ContinuityMetric[]
  regression: MockMetrics['regression']
  clubs?: string[]
  defaultClub?: string
  clubSeries?: Record<string, RoundMetric[]>
}

export interface MockMetrics {
  meta: {
    season: number
    round: number
    generatedAt: string
    note: string
    dataSource?: string
    defaultSeason?: number
    seasons?: number[]
  }
  leagueOverview: {
    avgUnavailableValue: number
    totalVflOnlyPvs?: number
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
    marginRSquared?: number
    coefficients: Record<string, number>
    interpretation: string
  }
  seasons?: Record<string, SeasonBundle>
  clubs?: string[]
  defaultClub?: string
}
