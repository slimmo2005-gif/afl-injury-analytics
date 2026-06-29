import { useCurrentSeason } from '../hooks/useCurrentSeason'
import DraftClassView from '../components/DraftClassView'

export default function DraftClass() {
  const { data, loading, error } = useCurrentSeason()
  return <DraftClassView draft={data?.draftClass} loading={loading} error={error} />
}
