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

export interface Core22RoleMetric {
  role: string
  roleId: string
  corrWin: number
  corrMargin: number
  avgMissPvs: number
  pctRounds: number
}

export interface Core22StarMiss {
  role: string
  roleId: string
  rounds: number
  winWhenMiss: number
  winOtherwise: number
  deltaPp: number
}

export interface Core22Coefficient {
  role: string
  roleId: string
  coef: number
}

export interface Core22MarginalImpact {
  role: string
  roleId: string
  winPctPer100: number
  marginPer100: number
}

export interface Core22Yearly {
  season: number
  total: number
  keyRoles: number
  keyForward: number
  keyDefender: number
  mid: number
}

export interface Core22Method {
  id: string
  label: string
  teamRounds: number
  avgMissedPvs: number
  avgPlayersMissed: number
  winRate: number
  correlations: Core22RoleMetric[]
  marginalImpact: Core22MarginalImpact[]
  starMiss: Core22StarMiss[]
  coefficients: Core22Coefficient[]
  archetypeModelR2: number
  keyVsOther: {
    keyRolesCoef: number
    otherRolesCoef: number
    r2: number
  }
  yearly: Core22Yearly[]
}

export interface Core22Impact {
  fromSeason: number
  toSeason: number
  starPvsThreshold: number
  methods: Core22Method[]
  interpretation: string
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
  core22Impact?: Core22Impact
}
