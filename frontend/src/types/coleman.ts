export interface ColemanWinner {
  year: number
  player: string
  club: string
  height_cm: number | null
  goals: number
  photo_url: string | null
  notes: string | null
  nickname: string | null
  coleman_medal: boolean
  season_incomplete: boolean
  tied_winner: boolean
}

export interface ColemanChallenger {
  player: string
  club: string
  height_cm: number
  current_goals: number
  coleman_position: number
  photo_url: string | null
  notes: string | null
}

export interface ColemanHeightsBundle {
  meta: {
    generatedAt: string
    source: string
    description: string
  }
  challenger: ColemanChallenger
  winners: ColemanWinner[]
}

export interface HeightBand {
  label: string
  min: number
  max: number | null
  count: number
  pct: number
}

export interface ColemanStats {
  totalMedallists: number
  withHeight: number
  shortest: ColemanWinner | null
  tallest: ColemanWinner | null
  averageHeight: number | null
  heightBands: HeightBand[]
  under180: number
  over195: number
  mostCommonBand: string
  shortestColemanMedallist: ColemanWinner | null
  royPark: ColemanWinner | null
  harryMcKay: ColemanWinner | null
}
