import { useEffect, useState } from 'react'
import { apiRequest } from '../lib/apiClient'

function formatTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return '--:--'
  }

  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function EmailsWidget() {
  const [emails, setEmails] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [urgentEmails, setUrgentEmails] = useState([])
  const [showUrgent, setShowUrgent] = useState(false)
  const [loadingUrgent, setLoadingUrgent] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')
  const [summary, setSummary] = useState(null)
  const [showSummary, setShowSummary] = useState(false)
  const [loadingSummary, setLoadingSummary] = useState(false)

  useEffect(() => {
    let isMounted = true

    const loadEmails = async () => {
      setIsLoading(true)
      setError('')

      try {
        const payload = await apiRequest('/api/v1/emails/list?limit=8&offset=0')
        const apiEmails = Array.isArray(payload?.emails) ? payload.emails : []

        if (!isMounted) {
          return
        }

        setEmails(apiEmails)
      } catch (loadError) {
        if (!isMounted) {
          return
        }

        const message = loadError instanceof Error ? loadError.message : 'Unable to load emails.'
        setError(message)
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    loadEmails()

    return () => {
      isMounted = false
    }
  }, [])

  const loadUrgentEmails = async () => {
    setLoadingUrgent(true)
    setError('')

    try {
      const payload = await apiRequest('/api/v1/emails/urgent')
      const urgent = Array.isArray(payload?.urgent_emails) ? payload.urgent_emails : 
                     Array.isArray(payload?.emails) ? payload.emails : 
                     payload?.critical_priority || []
      setUrgentEmails(urgent)
      setShowUrgent(true)
      
      if (urgent.length === 0) {
        setSuccessMessage('No urgent emails at the moment')
        setTimeout(() => setSuccessMessage(''), 3000)
      }
    } catch (urgentError) {
      const message = urgentError instanceof Error ? urgentError.message : 'Failed to load urgent emails'
      setError(message)
    } finally {
      setLoadingUrgent(false)
    }
  }

  const loadSummary = async () => {
    setLoadingSummary(true)
    setError('')

    try {
      const payload = await apiRequest('/api/v1/emails/summarize', {
        method: 'POST',
        body: JSON.stringify({ limit: 10, include_urgent_only: false }),
      })
      setSummary(payload?.summary || payload)
      setShowSummary(true)
      setSuccessMessage('Inbox summary generated')
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (summaryError) {
      const message = summaryError instanceof Error ? summaryError.message : 'Failed to generate summary'
      setError(message)
    } finally {
      setLoadingSummary(false)
    }
  }

  return (
    <article className="glass rounded-xl border border-white/10 p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-text-primary">Latest emails</h3>
          <p className="text-xs text-text-secondary">Live inbox snapshot from Gmail integration.</p>
        </div>
        <span className="rounded-full border border-white/15 bg-white/5 px-2.5 py-1 text-xs font-semibold text-text-secondary">
          {emails.length}
        </span>
      </div>

      {error && (
        <p className="mb-3 rounded-lg border border-red-300/20 bg-red-500/10 px-3 py-2 text-xs text-red-100" role="alert">
          {error}
        </p>
      )}

      {successMessage && (
        <p className="mb-3 rounded-lg border border-green-300/20 bg-green-500/10 px-3 py-2 text-xs text-green-100" role="status">
          ✓ {successMessage}
        </p>
      )}

      {isLoading ? (
        <div className="rounded-lg border border-white/10 bg-white/5 px-4 py-5 text-center animate-fade-in">
          <p className="text-sm font-semibold text-text-primary">Loading emails...</p>
        </div>
      ) : emails.length === 0 ? (
        <div className="rounded-lg border border-dashed border-white/20 bg-white/5 px-4 py-5 text-center animate-fade-in">
          <p className="text-sm font-semibold text-text-primary">No recent emails</p>
          <p className="mt-1 text-xs text-text-secondary">
            Connect Gmail or refresh later to see inbox items.
          </p>
        </div>
      ) : (
        <ul className="space-y-2" role="list" aria-label="Latest inbox messages">
          {emails.map((email) => (
            <li key={email.id} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-semibold text-text-primary">{email.subject || '(no subject)'}</p>
                <time className="text-xs text-text-secondary">{formatTime(email.timestamp)}</time>
              </div>
              <p className="mt-1 truncate text-xs text-text-secondary">{email.from_name || email.from_address}</p>
              <div className="mt-2 flex items-center justify-between gap-2">
                <p className="line-clamp-1 text-xs text-text-tertiary">{email.snippet || 'No preview available.'}</p>
                {email.is_unread && (
                  <span className="rounded-full border border-blue-300/30 bg-blue-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-200">
                    New
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Urgent Emails Section */}
      {showUrgent && urgentEmails.length > 0 && (
        <div className="mt-4 pt-4 border-t border-white/10 space-y-2">
          <p className="text-xs font-semibold text-red-300">⚠ Urgent ({urgentEmails.length}):</p>
          {urgentEmails.slice(0, 2).map((email) => (
            <div key={email.id} className="rounded border border-red-300/20 bg-red-500/5 px-2 py-1.5">
              <p className="truncate text-xs font-semibold text-red-200">{email.subject}</p>
              <p className="truncate text-xs text-red-100/70">{email.from_name || email.from_address}</p>
            </div>
          ))}
        </div>
      )}

      {/* Summary Section */}
      {showSummary && summary && (
        <div className="mt-4 pt-4 border-t border-white/10 space-y-2">
          <p className="text-xs font-semibold text-text-primary">📋 Summary:</p>
          <div className="rounded border border-white/10 bg-white/5 px-2 py-1.5">
            <p className="text-xs text-text-secondary line-clamp-3">
              {typeof summary === 'string' ? summary : summary.summary || 'Summary generated'}
            </p>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={loadUrgentEmails}
          disabled={loadingUrgent}
          className="
            touch-target flex-1 min-w-24 text-center text-xs font-semibold
            rounded border border-red-300/30 bg-red-500/10 text-red-200
            hover:bg-red-500/20 disabled:opacity-50 transition-colors
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400
          "
          aria-label="Check urgent emails"
        >
          {loadingUrgent ? '...' : '⚠ Urgent'}
        </button>
        <button
          type="button"
          onClick={loadSummary}
          disabled={loadingSummary}
          className="
            touch-target flex-1 min-w-24 text-center text-xs font-semibold
            rounded border border-blue-300/30 bg-blue-500/10 text-blue-200
            hover:bg-blue-500/20 disabled:opacity-50 transition-colors
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400
          "
          aria-label="Generate inbox summary"
        >
          {loadingSummary ? '...' : '📋 Summary'}
        </button>
        <button
          type="button"
          className="
            touch-target flex-1 min-w-24 text-center text-xs font-semibold
            rounded border border-white/15 bg-white/5 text-text-secondary
            hover:bg-white/10 transition-colors
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary
          "
          aria-label="View all emails"
        >
          Inbox →
        </button>
      </div>
    </article>
  )
}
