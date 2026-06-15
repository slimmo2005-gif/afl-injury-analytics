import { useState } from 'react'
import {
  fetchAdminFeedback,
  fetchAdminStats,
  fetchDeviceStatus,
  getAnalyticsBaseUrl,
  getOrCreateSessionId,
  isAnalyticsExcludedLocally,
  setDeviceSessionExclusion,
  type AdminFeedbackResponse,
  type AdminStatsResponse,
  type DeviceStatusResult,
  type FeedbackItem,
} from '../lib/analytics'

type AdminTab = 'visitors' | 'feedback'

type Props = {
  embedded?: boolean
}

function countryLabel(code: string): string {
  if (code === 'XX' || !code) return 'Unknown / not via Cloudflare'
  try {
    const name = new Intl.DisplayNames(['en'], { type: 'region' }).of(code)
    return name ? `${name} (${code})` : code
  } catch {
    return code
  }
}

function formatFeedbackTime(createdAt: string): string {
  try {
    return new Date(createdAt).toLocaleString('en-AU', {
      hour: 'numeric',
      minute: '2-digit',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return createdAt
  }
}

function FeedbackEntry({ item }: { item: FeedbackItem }) {
  const contacts = [
    item.contactEmail && `Email: ${item.contactEmail}`,
    item.contactWhatsapp && `WhatsApp: ${item.contactWhatsapp}`,
    item.contactDiscord && `Discord: ${item.contactDiscord}`,
  ].filter(Boolean)

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-sm">
      <div className="flex flex-wrap gap-2 text-xs text-slate-500 mb-2">
        <span>{formatFeedbackTime(item.createdAt)}</span>
        <span>{item.wordCount} words</span>
      </div>
      <p className="text-slate-200 whitespace-pre-wrap">{item.message}</p>
      {contacts.length > 0 && (
        <p className="text-xs text-slate-500 mt-2">{contacts.join(' · ')}</p>
      )}
    </div>
  )
}

export default function AdminAnalytics({ embedded = true }: Props) {
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deviceBusy, setDeviceBusy] = useState(false)
  const [deviceMessage, setDeviceMessage] = useState<string | null>(null)
  const [excludedLocally, setExcludedLocally] = useState(() => isAnalyticsExcludedLocally())
  const [deviceStatus, setDeviceStatus] = useState<Extract<DeviceStatusResult, { ok: true }> | null>(
    null,
  )
  const [tab, setTab] = useState<AdminTab>('visitors')
  const [stats, setStats] = useState<Extract<AdminStatsResponse, { ok: true }> | null>(null)
  const [feedback, setFeedback] = useState<Extract<AdminFeedbackResponse, { ok: true }> | null>(null)

  const configured = Boolean(getAnalyticsBaseUrl())
  const loaded = stats !== null || feedback !== null
  const sessionIdShort = (() => {
    try {
      const id = getOrCreateSessionId()
      return `${id.slice(0, 8)}…`
    } catch {
      return '—'
    }
  })()

  async function refreshVisitorPanel(pwd: string) {
    const [statsResult, statusResult] = await Promise.all([
      fetchAdminStats(pwd),
      fetchDeviceStatus(pwd),
    ])
    if (statsResult.ok) setStats(statsResult)
    if (statusResult.ok) {
      setDeviceStatus(statusResult)
      setExcludedLocally(statusResult.isExcluded || isAnalyticsExcludedLocally())
    }
    return { statsResult, statusResult }
  }

  async function toggleDeviceExclusion(exclude: boolean) {
    if (!password.trim()) {
      setDeviceMessage('Enter your admin password above first.')
      return
    }
    setDeviceBusy(true)
    setDeviceMessage(null)
    setError(null)
    const pwd = password.trim()
    const result = await setDeviceSessionExclusion(pwd, exclude)
    if (!result.ok) {
      setDeviceBusy(false)
      setDeviceMessage(result.error)
      return
    }
    setExcludedLocally(exclude)
    await refreshVisitorPanel(pwd)
    setDeviceBusy(false)
    setDeviceMessage(
      exclude
        ? 'This browser is excluded from visitor counts.'
        : 'This browser can be counted again — visit the club page once to log a session.',
    )
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setStats(null)
    setFeedback(null)
    setLoading(true)
    try {
      const pwd = password.trim()
      const [statsResult, feedbackResult] = await Promise.all([
        fetchAdminStats(pwd),
        fetchAdminFeedback(pwd),
      ])
      if (!statsResult.ok) {
        setError(statsResult.error)
        return
      }
      if (!feedbackResult.ok) {
        setError(feedbackResult.error)
        return
      }
      setStats(statsResult)
      setFeedback(feedbackResult)
      const statusResult = await fetchDeviceStatus(pwd)
      if (statusResult.ok) setDeviceStatus(statusResult)
    } catch {
      setError('Could not reach the analytics server.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={embedded ? '' : 'min-h-screen p-6'}>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-afl-gold">Visitor analytics & feedback</h1>
        <p className="text-sm text-slate-500 mt-1">
          Login sessions and user feedback via Cloudflare worker — see workers/afl-analytics-worker/SETUP.txt
        </p>
      </div>

      {!configured && (
        <p className="text-sm text-amber-400/90 rounded border border-amber-500/30 bg-amber-500/10 px-4 py-3 mb-6">
          VITE_ANALYTICS_API_URL is not set. Visits are not recorded and this panel cannot load stats.
        </p>
      )}

      <form onSubmit={handleSubmit} className="flex flex-wrap gap-3 items-end mb-6">
        <label className="flex flex-col gap-1 text-xs text-slate-500">
          Admin password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 min-w-[200px]"
            placeholder="Worker secret"
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 text-sm rounded bg-afl-green text-afl-gold font-medium disabled:opacity-50"
        >
          {loading ? 'Loading…' : 'Load data'}
        </button>
      </form>

      {error && <p className="text-sm text-red-400 mb-4">{error}</p>}

      {configured && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 mb-6 text-sm">
          <h3 className="text-slate-300 font-medium mb-2">Your devices</h3>
          <p className="text-xs text-slate-500 mb-3">
            Exclude this browser from visitor counts. The club page logs a visit; admin routes do not.
          </p>
          <div className="flex flex-wrap gap-4 text-xs text-slate-400 mb-3">
            <span>
              Session: <code className="text-slate-300">{sessionIdShort}</code>
            </span>
            <span>
              This device:{' '}
              {deviceStatus
                ? deviceStatus.isExcluded
                  ? 'Excluded'
                  : deviceStatus.countsInVisitorStats
                    ? `Counted (${deviceStatus.country ?? '?'})`
                    : 'Not in logs yet'
                : excludedLocally
                  ? 'Excluded (local)'
                  : 'Load data to check'}
            </span>
          </div>
          <button
            type="button"
            disabled={deviceBusy}
            onClick={() => void toggleDeviceExclusion(!excludedLocally)}
            className="text-xs px-3 py-1.5 rounded border border-slate-700 text-slate-300 hover:text-white disabled:opacity-40"
          >
            {deviceBusy ? 'Updating…' : excludedLocally ? 'Include this device' : 'Exclude this device'}
          </button>
          {deviceMessage && <p className="text-xs text-slate-500 mt-2">{deviceMessage}</p>}
        </div>
      )}

      {loaded && (
        <div className="flex gap-1 border-b border-slate-800 mb-6">
          <button
            type="button"
            onClick={() => setTab('visitors')}
            className={`px-3 py-2 text-xs font-medium border-b-2 -mb-px ${
              tab === 'visitors'
                ? 'border-cyan-500 text-white'
                : 'border-transparent text-slate-500 hover:text-slate-300'
            }`}
          >
            Visitors
          </button>
          <button
            type="button"
            onClick={() => setTab('feedback')}
            className={`px-3 py-2 text-xs font-medium border-b-2 -mb-px ${
              tab === 'feedback'
                ? 'border-cyan-500 text-white'
                : 'border-transparent text-slate-500 hover:text-slate-300'
            }`}
          >
            Feedback{feedback ? ` (${feedback.total})` : ''}
          </button>
        </div>
      )}

      {stats && tab === 'visitors' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 max-w-md">
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <p className="text-xs text-slate-500">Visitor sessions</p>
              <p className="text-2xl font-semibold text-slate-100 tabular-nums">
                {stats.totalSessions.toLocaleString()}
              </p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <p className="text-xs text-slate-500">Excluded devices</p>
              <p className="text-2xl font-semibold text-slate-100 tabular-nums">
                {stats.excludedDeviceCount.toLocaleString()}
              </p>
            </div>
          </div>

          {stats.byDay.length > 0 && (
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b border-slate-800">
                    <th className="px-4 py-2">Date (UTC)</th>
                    <th className="px-4 py-2">Sessions</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.byDay.map((row) => (
                    <tr key={row.day} className="border-b border-slate-800/50">
                      <td className="px-4 py-2 text-slate-300">{row.day}</td>
                      <td className="px-4 py-2 tabular-nums">{row.count.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b border-slate-800">
                  <th className="px-4 py-2">Country</th>
                  <th className="px-4 py-2">Sessions</th>
                </tr>
              </thead>
              <tbody>
                {stats.byCountry.length === 0 ? (
                  <tr>
                    <td colSpan={2} className="px-4 py-4 text-slate-500">
                      No data yet.
                    </td>
                  </tr>
                ) : (
                  stats.byCountry.map((row) => (
                    <tr key={row.country} className="border-b border-slate-800/50">
                      <td className="px-4 py-2 text-slate-300">{countryLabel(row.country)}</td>
                      <td className="px-4 py-2 tabular-nums">{row.count.toLocaleString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {feedback && tab === 'feedback' && (
        <div className="space-y-6">
          {feedback.byDay.length === 0 ? (
            <p className="text-slate-500">No feedback yet.</p>
          ) : (
            feedback.byDay.map((group) => (
              <div key={group.day}>
                <h3 className="text-sm font-medium text-slate-400 mb-3">
                  {group.day} ({group.items.length} submission
                  {group.items.length === 1 ? '' : 's'})
                </h3>
                <div className="space-y-3">
                  {group.items.map((item) => (
                    <FeedbackEntry key={item.id} item={item} />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
