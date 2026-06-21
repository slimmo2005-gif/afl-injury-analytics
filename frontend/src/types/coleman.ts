export interface ColemanWinner {
  year: number
  player: string
  club: string
  height_cm: number | null
  goals: number
  photo_url: string | null
  notes: string | null
  nickname: string | null
  /** Coleman Medallist (1955+; first presented 1981, 1955–1980 retrospective) */
  coleman_medal: boolean
  /** Leading Goalkicker Medallist (1897–1954) */
  leading_goalkicker_medal: boolean
  award: 'Coleman Medal' | 'Leading Goalkicker Medal'
  coleman_retrospective: boolean
  coleman_presented_live: boolean
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
  nickname: string | null
  notes: string | null
}

export interface AwardHistory {
  colemanFirstPresented: number
  colemanRetrospectiveFrom: number
  leadingGoalkickerMedalThrough: number
  retrospectiveRecognitionYear: number
  medalsPresentedYear: number
  summary: string
}

export interface ColemanHeightsBundle {
  meta: {
    generatedAt: string
    source: string
    description: string
    awardHistory: AwardHistory
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
  totalColemanMedallists: number
  totalLeadingGoalkickerMedallists: number
  withHeight: number
  shortest: ColemanWinner | null
  tallest: ColemanWinner | null
  averageHeight: number | null
  heightBands: HeightBand[]
  under180: number
  over195: number
  mostCommonBand: string
  shortestColemanMedallist: ColemanWinner | null
  shortestLeadingGoalkickerMedallist: ColemanWinner | null
  royPark: ColemanWinner | null
  harryMcKay: ColemanWinner | null
}
