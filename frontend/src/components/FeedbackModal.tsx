import { useMemo, useState } from 'react'
import { getAnalyticsBaseUrl, submitFeedback } from '../lib/analytics'
import { countWords } from '../utils/countWords'

const MAX_WORDS = 200

type Props = {
  onClose: () => void
}

export function FeedbackModal({ onClose }: Props) {
  const [message, setMessage] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [contactWhatsapp, setContactWhatsapp] = useState('')
  const [contactDiscord, setContactDiscord] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)

  const wordCount = useMemo(() => countWords(message), [message])
  const overLimit = wordCount > MAX_WORDS
  const configured = Boolean(getAnalyticsBaseUrl())

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!message.trim()) {
      setError('Please enter a message.')
      return
    }
    if (overLimit) {
      setError(`Please keep your message to ${MAX_WORDS} words or fewer.`)
      return
    }
    setSubmitting(true)
    try {
      const result = await submitFeedback({
        message: message.trim(),
        contactEmail: contactEmail.trim() || undefined,
        contactWhatsapp: contactWhatsapp.trim() || undefined,
        contactDiscord: contactDiscord.trim() || undefined,
      })
      if (!result.ok) {
        setError(result.error)
        return
      }
      setSent(true)
    } catch {
      setError('Something went wrong. Please try again later.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="feedback-title"
    >
      <div
        className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-4 border-b border-slate-800">
          <h2 id="feedback-title" className="text-lg font-semibold text-slate-100">
            Provide feedback
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Suggestions, corrections, or questions — optional contact if you want a reply.
          </p>
        </div>

        <div className="px-5 py-4">
          {sent ? (
            <div className="text-center py-6">
              <p className="text-emerald-400 font-medium">Thank you</p>
              <p className="text-sm text-slate-400 mt-2">Your feedback has been submitted.</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {!configured && (
                <p className="text-xs text-amber-400/90 rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2">
                  Feedback is not available on this build (analytics API URL missing).
                </p>
              )}

              <label className="block">
                <span className="text-xs text-slate-500">Message (max {MAX_WORDS} words)</span>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={6}
                  className="mt-1 w-full px-3 py-2 rounded bg-slate-950 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:ring-1 focus:ring-cyan-500 resize-y min-h-[120px]"
                  placeholder="What would you like to share?"
                  disabled={!configured}
                />
                <span className="text-xs text-slate-600 mt-1 block">
                  {wordCount} / {MAX_WORDS} words
                </span>
              </label>

              <p className="text-xs text-slate-500">Optional — only if you want a response:</p>
              <div className="grid gap-3 sm:grid-cols-3">
                <label className="block">
                  <span className="text-xs text-slate-500">Email</span>
                  <input
                    type="email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    className="mt-1 w-full px-3 py-2 rounded bg-slate-950 border border-slate-700 text-slate-100 text-sm"
                    placeholder="you@example.com"
                    disabled={!configured}
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-slate-500">WhatsApp</span>
                  <input
                    value={contactWhatsapp}
                    onChange={(e) => setContactWhatsapp(e.target.value)}
                    className="mt-1 w-full px-3 py-2 rounded bg-slate-950 border border-slate-700 text-slate-100 text-sm"
                    placeholder="Phone or handle"
                    disabled={!configured}
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-slate-500">Discord</span>
                  <input
                    value={contactDiscord}
                    onChange={(e) => setContactDiscord(e.target.value)}
                    className="mt-1 w-full px-3 py-2 rounded bg-slate-950 border border-slate-700 text-slate-100 text-sm"
                    placeholder="Username"
                    disabled={!configured}
                  />
                </label>
              </div>

              {error && <p className="text-sm text-red-400">{error}</p>}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!configured || submitting}
                  className="px-4 py-2 text-sm rounded bg-afl-green text-afl-gold font-medium hover:opacity-90 disabled:opacity-40"
                >
                  {submitting ? 'Sending…' : 'Send feedback'}
                </button>
              </div>
            </form>
          )}
        </div>

        {sent && (
          <div className="px-5 pb-4 flex justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm rounded border border-slate-700 text-slate-300 hover:text-white"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
