import { useParams } from 'react-router-dom'
import { useCurrentSeason } from '../hooks/useCurrentSeason'
import DraftClassView from '../components/DraftClassView'

export default function DraftClass() {
  const { year } = useParams<{ year: string }>()
  const draftYear = year === '2026' ? 2026 : 2025
  const { data, loading, error } = useCurrentSeason()

  const draft = draftYear === 2026 ? data?.draftClass2026 : data?.draftClass

  return <DraftClassView draft={draft} loading={loading} error={error} />
}
