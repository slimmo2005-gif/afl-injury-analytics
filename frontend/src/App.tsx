import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { FilterProvider } from './context/FilterContext'
import { MetricsProvider } from './context/MetricsContext'
import ClubDetail from './pages/ClubDetail'
import LeagueOverview from './pages/LeagueOverview'
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
      <Route element={<Layout />}>
        <Route index element={<LeagueOverview />} />
        <Route path="club" element={<ClubDetail />} />
        <Route path="season" element={<SeasonExplorer />} />
        <Route path="player" element={<PlayerExplorer />} />
        <Route path="trends" element={<Trends />} />
        <Route path="model" element={<ModelInsights />} />
        <Route path="roles" element={<RoleImpact />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
    </FilterProvider>
    </MetricsProvider>
  )
}
