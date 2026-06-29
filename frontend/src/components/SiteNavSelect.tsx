import { useLocation, useNavigate } from 'react-router-dom'
import { CURRENT_SEASON, UKRAINE_TRACKER_URL } from '../constants'

type NavRoute = { kind: 'route'; path: string; label: string }
type NavExternal = { kind: 'external'; href: string; label: string }

const NAV_ITEMS: Array<NavRoute | NavExternal> = [
  { kind: 'route', path: '/', label: 'Club injury view (2021–2025)' },
  { kind: 'route', path: '/current', label: `${CURRENT_SEASON} live season` },
  { kind: 'route', path: '/injury-impact', label: 'Weekly selection impact' },
  { kind: 'route', path: '/draft-class/2025', label: '2025 draft class — first round' },
  { kind: 'route', path: '/draft-class/2026', label: '2026 draft class — first round' },
  { kind: 'route', path: '/coleman-heights', label: 'Coleman heights story' },
  { kind: 'external', href: UKRAINE_TRACKER_URL, label: 'Ukraine War Territory Tracker ↗' },
]

export default function SiteNavSelect() {
  const location = useLocation()
  const navigate = useNavigate()

  const active =
    NAV_ITEMS.find((item) => item.kind === 'route' && item.path === location.pathname)?.path ??
    NAV_ITEMS[0].path

  return (
    <label className="flex flex-col gap-1 text-xs text-slate-500">
      <span className="sr-only">Choose page</span>
      <select
        value={active}
        onChange={(e) => {
          const value = e.target.value
          const item = NAV_ITEMS.find((entry) =>
            entry.kind === 'route' ? entry.path === value : entry.href === value,
          )
          if (!item) return
          if (item.kind === 'external') {
            window.open(item.href, '_blank', 'noopener,noreferrer')
            return
          }
          navigate(item.path)
        }}
        className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 min-w-[220px] max-w-[300px]"
        aria-label="Choose page"
      >
        {NAV_ITEMS.map((item) => (
          <option
            key={item.kind === 'route' ? item.path : item.href}
            value={item.kind === 'route' ? item.path : item.href}
          >
            {item.label}
          </option>
        ))}
      </select>
    </label>
  )
}
