import { useEffect, useMemo, useState } from 'react'
import { apiRequest } from '../lib/apiClient'

/**
 * Activity / Insights Widget Component
 * Features: productivity metrics, tasks completed, emails handled
 * Visualization: progress bars and key metrics
 * Accessibility: semantic structure with aria-labels for metrics
 */
export default function ActivityWidget() {
  const [tasks, setTasks] = useState([])
  const [emails, setEmails] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let isMounted = true

    const loadActivity = async () => {
      setIsLoading(true)
      setError('')

      try {
        const [taskPayload, emailPayload] = await Promise.all([
          apiRequest('/api/v1/tasks?limit=100&offset=0'),
          apiRequest('/api/v1/emails/list?limit=50&offset=0'),
        ])

        if (!isMounted) {
          return
        }

        setTasks(Array.isArray(taskPayload?.tasks) ? taskPayload.tasks : [])
        setEmails(Array.isArray(emailPayload?.emails) ? emailPayload.emails : [])
      } catch (loadError) {
        if (!isMounted) {
          return
        }

        const message = loadError instanceof Error ? loadError.message : 'Unable to load activity metrics.'
        setError(message)
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    loadActivity()

    return () => {
      isMounted = false
    }
  }, [])

  const metrics = useMemo(() => {
    const totalTasks = tasks.length
    const completedTasks = tasks.filter((task) => task.status === 'completed').length
    const processedEmails = emails.filter((email) => !email.is_unread).length
    const totalEmails = Math.max(emails.length, 1)
    const scoreBase = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0
    const inboxSignal = Math.round((processedEmails / totalEmails) * 20)
    const productivityScore = Math.min(100, scoreBase + inboxSignal)

    return [
      {
        label: 'Productivity Score',
        value: productivityScore,
        max: 100,
        color: 'gradient-primary',
        icon: '📈',
      },
      {
        label: 'Tasks Completed',
        value: completedTasks,
        max: Math.max(totalTasks, 1),
        color: 'bg-green-500',
        icon: '✓',
      },
      {
        label: 'Emails Processed',
        value: processedEmails,
        max: Math.max(emails.length, 1),
        color: 'bg-blue-500',
        icon: '📧',
      },
    ]
  }, [emails, tasks])

  const completedTasks = tasks.filter((task) => task.status === 'completed').length
  const remainingTasks = Math.max(tasks.length - completedTasks, 0)
  const unreadEmails = emails.filter((email) => email.is_unread).length

  return (
    <article className="glass rounded-xl border border-white/10 p-5">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-base font-semibold text-text-primary">Today&apos;s activity</h3>
        <p className="text-xs text-text-secondary">Performance snapshot across key channels.</p>
      </div>

      {error && (
        <p className="mb-3 rounded-lg border border-red-300/20 bg-red-500/10 px-3 py-2 text-xs text-red-100" role="alert">
          {error}
        </p>
      )}

      {/* Metrics Grid */}
      {isLoading ? (
        <div className="rounded-lg border border-white/10 bg-white/5 px-4 py-5 text-center animate-fade-in">
          <p className="text-sm font-semibold text-text-primary">Loading activity...</p>
        </div>
      ) : metrics.length === 0 ? (
        <div className="rounded-lg border border-dashed border-white/20 bg-white/5 px-4 py-5 text-center animate-fade-in">
          <p className="text-sm font-semibold text-text-primary">No activity yet</p>
          <p className="mt-1 text-xs text-text-secondary">Metrics will appear as your workday progresses.</p>
        </div>
      ) : (
        <div className="space-y-4" role="region" aria-label="Daily activity metrics">
          {metrics.map((metric, index) => {
            const percentage = (metric.value / metric.max) * 100

            return (
              <div key={index} className="space-y-2">
                {/* Label and Icon */}
                <div className="flex items-center justify-between">
                  <p className="flex items-center gap-2 text-sm font-medium text-text-primary">
                    <span aria-hidden="true">{metric.icon}</span>
                    {metric.label}
                  </p>
                  <span
                    className="text-sm font-semibold text-secondary"
                    aria-label={`${metric.value} out of ${metric.max}`}
                  >
                    {metric.value}/{metric.max}
                  </span>
                </div>

                {/* Progress Bar */}
                <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
                  <div
                    className={`h-full ${metric.color} transition-all duration-500`}
                    style={{ width: `${percentage}%` }}
                    role="progressbar"
                    aria-valuenow={metric.value}
                    aria-valuemin="0"
                    aria-valuemax={metric.max}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Summary Stats */}
      <div className="mt-6 pt-4 border-t border-white/10 space-y-2">
        <p className="text-xs text-text-secondary">
          <span className="font-semibold text-text-primary">{completedTasks}</span> tasks completed today
        </p>
        <p className="text-xs text-text-secondary">
          <span className="font-semibold text-text-primary">{remainingTasks}</span> tasks remaining, {unreadEmails} unread emails
        </p>
      </div>

      {/* View Insights Link */}
      <button
        type="button"
        className="
          touch-target mt-4 w-full text-center text-sm text-secondary hover:text-secondary/80
          py-2 rounded transition-colors focus-visible:outline-none
          focus-visible:ring-2 focus-visible:ring-secondary
        "
        aria-label="View detailed insights"
      >
        View insights →
      </button>
    </article>
  )
}
