import { Navigate, Route, Routes } from 'react-router-dom'
import AdminLayout from './components/AdminLayout'
import ClubLayout from './components/ClubLayout'
import StoryLayout from './components/StoryLayout'
import { FilterProvider } from './context/FilterContext'
import { MetricsProvider } from './context/MetricsContext'
import AdminAnalytics from './pages/AdminAnalytics'
import AdminInsights from './pages/AdminInsights'
import ClubDetail from './pages/ClubDetail'
import ColemanHeights from './pages/ColemanHeights'
import CurrentSeason from './pages/CurrentSeason'
import DraftClass from './pages/DraftClass'
import WeeklyTeamImpact from './pages/WeeklyTeamImpact'
import LeagueOverview from './pages/LeagueOverview'
import Methodology from './pages/Methodology'
import ModelInsights from './pages/ModelInsights'
import PlayerExplorer from './pages/PlayerExplorer'
import RoleImpact from './pages/RoleImpact'
import SeasonExplorer from './pages/SeasonExplorer'
import Trends from './pages/Trends'

export default function App() {
  return (
    <MetricsProvider>
      <FilterProvider>
        <Routes>
          <Route element={<ClubLayout />}>
            <Route index element={<ClubDetail />} />
            <Route path="current" element={<CurrentSeason />} />
            <Route path="draft-class" element={<Navigate to="/draft-class/2025" replace />} />
            <Route path="draft-class/:year" element={<DraftClass />} />
            <Route path="injury-impact" element={<WeeklyTeamImpact />} />
            <Route path="methodology" element={<Methodology />} />
          </Route>
          <Route element={<StoryLayout />}>
            <Route path="coleman-heights" element={<ColemanHeights />} />
          </Route>
          <Route path="admin" element={<AdminLayout />}>
            <Route index element={<LeagueOverview />} />
            <Route path="insights" element={<AdminInsights />} />
            <Route path="season" element={<SeasonExplorer />} />
            <Route path="player" element={<PlayerExplorer />} />
            <Route path="trends" element={<Trends />} />
            <Route path="model" element={<ModelInsights />} />
            <Route path="roles" element={<RoleImpact />} />
            <Route path="analytics" element={<AdminAnalytics />} />
          </Route>
          <Route path="club" element={<Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </FilterProvider>
    </MetricsProvider>
  )
}
