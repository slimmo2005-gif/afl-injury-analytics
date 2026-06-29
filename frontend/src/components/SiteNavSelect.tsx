import { useLocation, useNavigate } from 'react-router-dom'
import { CURRENT_SEASON } from '../constants'

const NAV_ITEMS = [
  { path: '/', label: 'Club injury view (2021–2025)' },
  { path: '/current', label: `${CURRENT_SEASON} live season` },
  { path: '/injury-impact', label: 'Weekly selection impact' },
  { path: '/draft-class', label: `${CURRENT_SEASON - 1} draft class — first round` },
  { path: '/coleman-heights', label: 'Coleman heights story' },
] as const

export default function SiteNavSelect() {
  const location = useLocation()
  const navigate = useNavigate()

  const active =
    NAV_ITEMS.find((item) => item.path === location.pathname)?.path ?? NAV_ITEMS[0].path

  return (
    <label className="flex flex-col gap-1 text-xs text-slate-500">
      <span className="sr-only">Choose page</span>
      <select
        value={active}
        onChange={(e) => navigate(e.target.value)}
        className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 min-w-[220px] max-w-[280px]"
        aria-label="Choose page"
      >
        {NAV_ITEMS.map((item) => (
          <option key={item.path} value={item.path}>
            {item.label}
          </option>
        ))}
      </select>
    </label>
  )
}
