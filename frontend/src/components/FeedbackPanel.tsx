import { getAnalyticsBaseUrl } from '../lib/analytics'

type Props = {
  onOpen: () => void
}

/** Visible feedback call-to-action on the main club page. */
export default function FeedbackPanel({ onOpen }: Props) {
  const configured = Boolean(getAnalyticsBaseUrl())

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
      <h3 className="text-sm font-medium text-slate-300">Feedback</h3>
      <p className="text-xs text-slate-500 mt-1 mb-3">
        Spot an error, have a suggestion, or want a feature? Tell us — submissions appear in the
        admin analytics panel.
      </p>
      <button
        type="button"
        onClick={onOpen}
        className="text-sm px-4 py-2 rounded-lg border border-slate-700 bg-slate-800 text-slate-200 hover:border-cyan-500/50 hover:text-cyan-200 transition-colors"
      >
        Send feedback
      </button>
      {!configured && (
        <p className="text-[11px] text-slate-600 mt-2">
          Feedback storage requires VITE_ANALYTICS_API_URL at build time.
        </p>
      )}
    </div>
  )
}
