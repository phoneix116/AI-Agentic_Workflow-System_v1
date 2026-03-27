import { useEffect, useMemo, useState } from 'react'
import { apiRequest } from '../lib/apiClient'

/**
 * Calendar Widget Component
 * Features: daily schedule view, highlight current time, color-coded events
 * Accessibility: semantic time elements, aria-labels for events
 * Responsive: adapts to widget container
 */
export default function CalendarWidget() {
  const now = new Date()
  const [events, setEvents] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [freeSlots, setFreeSlots] = useState([])
  const [showFreeSlots, setShowFreeSlots] = useState(false)
  const [loadingSlots, setLoadingSlots] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')

  useEffect(() => {
    let isMounted = true

    const loadSchedule = async () => {
      setIsLoading(true)
      setError('')

      const today = new Date().toISOString().slice(0, 10)
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'

      try {
        const payload = await apiRequest('/api/v1/calendar/daily-schedule', {
          method: 'POST',
          body: JSON.stringify({ date: today, timezone }),
        })

        const apiEvents = Array.isArray(payload?.events)
          ? payload.events
          : Array.isArray(payload?.data?.events)
            ? payload.data.events
            : []

        if (!isMounted) {
          return
        }

        setEvents(apiEvents)
      } catch (loadError) {
        if (!isMounted) {
          return
        }

        const message = loadError instanceof Error ? loadError.message : 'Unable to load calendar events.'
        setError(message)
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    loadSchedule()

    return () => {
      isMounted = false
    }
  }, [])

  const loadFreeSlots = async () => {
    setLoadingSlots(true)
    setError('')

    try {
      const today = new Date().toISOString().slice(0, 10)
      const payload = await apiRequest('/api/v1/calendar/free-slots', {
        method: 'POST',
        body: JSON.stringify({ date: today, min_duration_minutes: 30 }),
      })

      const slots = Array.isArray(payload?.free_slots) ? payload.free_slots : []
      setFreeSlots(slots)
      setShowFreeSlots(true)
      if (slots.length === 0) {
        setSuccessMessage('No free slots available today')
        setTimeout(() => setSuccessMessage(''), 3000)
      }
    } catch (slotError) {
      const message = slotError instanceof Error ? slotError.message : 'Failed to load free slots'
      setError(message)
    } finally {
      setLoadingSlots(false)
    }
  }

  const currentTime = now.getHours() * 60 + now.getMinutes()

  const displayEvents = useMemo(
    () => events.map((event, index) => {
      const startDate = new Date(event.start_time)
      const endDate = new Date(event.end_time)

      return {
        id: event.id || `${index}-${event.title}`,
        title: event.title || 'Untitled event',
        start: startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        end: endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        startMinutes: (startDate.getHours() * 60) + startDate.getMinutes(),
        endMinutes: (endDate.getHours() * 60) + endDate.getMinutes(),
      }
    }),
    [events],
  )

  return (
    <article className="glass rounded-xl border border-white/10 p-5">
      {/* Header */}
      <div className="mb-3">
        <h3 className="text-base font-semibold text-text-primary">Today&apos;s schedule</h3>
        <p className="text-xs text-text-secondary">Focus on the next confirmed blocks.</p>
      </div>

      {/* Current time indicator */}
      <div className="mb-3 text-xs text-text-secondary">
        {now.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
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

      {/* Compact Schedule View */}
      {isLoading ? (
        <div className="rounded-lg border border-white/10 bg-white/5 px-4 py-5 text-center animate-fade-in">
          <p className="text-sm font-semibold text-text-primary">Loading schedule...</p>
        </div>
      ) : displayEvents.length === 0 ? (
        <div className="rounded-lg border border-dashed border-white/20 bg-white/5 px-4 py-5 text-center animate-fade-in">
          <p className="text-sm font-semibold text-text-primary">No meetings scheduled</p>
          <p className="mt-1 text-xs text-text-secondary">
            You have a clear calendar window right now.
          </p>
        </div>
      ) : (
        <div className="space-y-1" role="list" aria-label="Today's events">
          {displayEvents.map((event) => {
            const isCurrentEvent = currentTime >= event.startMinutes && currentTime < event.endMinutes

            return (
              <div
                key={event.id}
                className={`
                  min-h-11 flex items-center gap-2 rounded border px-3 py-2 text-sm
                  transition-all bg-blue-500/15 border-blue-400/40 text-blue-100
                  ${isCurrentEvent ? 'ring-2 ring-secondary/50 glow' : ''}
                `}
                role="listitem"
                aria-label={`${event.title} from ${event.start} to ${event.end}`}
              >
                <time className="w-12 flex-shrink-0 font-mono font-semibold">
                  {event.start}
                </time>
                <span className="flex-1 truncate">{event.title}</span>
                {isCurrentEvent && (
                  <span className="text-xs font-bold animate-pulse">Now</span>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Free Slots Section */}
      {showFreeSlots && (
        <div className="mt-4 pt-4 border-t border-white/10 space-y-2">
          <p className="text-xs font-semibold text-text-primary">Available slots:</p>
          {loadingSlots ? (
            <p className="text-xs text-text-secondary">Loading...</p>
          ) : freeSlots.length === 0 ? (
            <p className="text-xs text-text-tertiary">No free slots available</p>
          ) : (
            <div className="space-y-1">
              {freeSlots.slice(0, 3).map((slot, idx) => (
                <p key={idx} className="text-xs text-text-secondary">
                  {slot.start_time && new Date(slot.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - 
                  {slot.end_time && new Date(slot.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={loadFreeSlots}
          disabled={loadingSlots}
          className="
            touch-target flex-1 text-center text-xs font-semibold
            rounded border border-secondary/30 bg-secondary/10 text-secondary
            hover:bg-secondary/20 disabled:opacity-50 transition-colors
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary
          "
          aria-label="Find free slots"
        >
          {loadingSlots ? '...' : 'Find free slots'}
        </button>
        <button
          type="button"
          className="
            touch-target flex-1 text-center text-xs font-semibold
            rounded border border-white/15 bg-white/5 text-text-secondary
            hover:bg-white/10 transition-colors
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary
          "
          aria-label="View full calendar"
        >
          View calendar →
        </button>
      </div>
    </article>
  )
}
