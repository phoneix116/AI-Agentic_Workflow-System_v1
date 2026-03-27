import { useState, useEffect } from 'react'
import { apiRequest } from '../lib/apiClient'

export default function Login({ onLoginSuccess }) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [oauthUrls, setOauthUrls] = useState({ gmail: null, calendar: null })

  useEffect(() => {
    loadOAuthUrls()
  }, [])

  const loadOAuthUrls = async () => {
    try {
      const [gmailRes, calendarRes] = await Promise.all([
        apiRequest('/api/v1/emails/oauth/authorize-url'),
        apiRequest('/api/v1/calendar/oauth-authorize'),
      ])
      setOauthUrls({
        gmail: gmailRes?.auth_url,
        calendar: calendarRes?.oauth_url,
      })
    } catch (err) {
      setError('Failed to load OAuth options. Try refreshing.')
    }
  }

  const handleLogin = async () => {
    setIsLoading(true)
    setError('')

    try {
      const response = await apiRequest('/api/v1/health/dev/token', {
        method: 'POST',
      })

      if (response?.data?.token) {
        window.localStorage.setItem('ai_assistant_token', response.data.token)
      } else if (response?.token) {
        window.localStorage.setItem('ai_assistant_token', response.token)
      }

      onLoginSuccess?.()
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleGmailConnect = () => {
    if (oauthUrls.gmail) {
      window.location.href = oauthUrls.gmail
    }
  }

  const handleCalendarConnect = () => {
    if (oauthUrls.calendar) {
      window.location.href = oauthUrls.calendar
    }
  }

  return (
    <div className="min-h-screen bg-background-DEFAULT flex items-center justify-center p-4">
      {/* Gradient background */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(0,212,255,0.16),_transparent_42%),radial-gradient(circle_at_bottom_right,_rgba(108,99,255,0.24),_transparent_42%)]"
      />

      <article className="glass relative z-10 rounded-2xl border border-white/10 p-8 md:p-12 w-full max-w-md shadow-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="h-16 w-16 mx-auto mb-4 rounded-2xl gradient-primary flex items-center justify-center shadow-glow">
            <span className="text-4xl font-bold text-white glow">🧠</span>
          </div>
          <h1 className="text-3xl font-bold text-text-primary mb-2">Astra</h1>
          <p className="text-sm text-text-secondary">Your AI Assistant for Email, Calendar & Tasks</p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 rounded-lg border border-red-300/20 bg-red-500/10 p-4">
            <p className="text-sm text-red-100">{error}</p>
          </div>
        )}

        {/* Login Section */}
        <div className="space-y-4 mb-6">
          <button
            type="button"
            onClick={handleLogin}
            disabled={isLoading}
            className="
              w-full py-3 px-4 rounded-lg font-semibold text-white
              gradient-primary hover:glow-lg hover:scale-105
              disabled:opacity-50 disabled:scale-100
              transition-all duration-200
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary
            "
            aria-label="Login to Astra"
          >
            {isLoading ? 'Signing in...' : 'Sign in to Astra'}
          </button>

          <p className="text-xs text-center text-text-tertiary">
            By signing in, you agree to connect your Gmail and Calendar.
          </p>
        </div>

        {/* OAuth Divider */}
        <div className="my-6 flex items-center gap-3">
          <div className="flex-1 h-px bg-white/10" />
          <span className="text-xs text-text-tertiary">Optional: Connect Services</span>
          <div className="flex-1 h-px bg-white/10" />
        </div>

        {/* OAuth Buttons */}
        <div className="space-y-3 mb-6">
          <button
            type="button"
            onClick={handleGmailConnect}
            disabled={!oauthUrls.gmail || isLoading}
            className="
              w-full py-3 px-4 rounded-lg font-semibold
              border border-white/15 bg-white/5 text-text-primary
              hover:bg-white/10 hover:border-secondary/40
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-all duration-200
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary
            "
            aria-label="Connect Gmail"
          >
            📧 Connect Gmail
          </button>

          <button
            type="button"
            onClick={handleCalendarConnect}
            disabled={!oauthUrls.calendar || isLoading}
            className="
              w-full py-3 px-4 rounded-lg font-semibold
              border border-white/15 bg-white/5 text-text-primary
              hover:bg-white/10 hover:border-secondary/40
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-all duration-200
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary
            "
            aria-label="Connect Google Calendar"
          >
            📅 Connect Calendar
          </button>
        </div>

        {/* Info Text */}
        <div className="rounded-lg border border-blue-300/20 bg-blue-500/10 p-4 text-center">
          <p className="text-xs text-blue-100 leading-relaxed">
            💡 <span className="font-semibold">Tip:</span> Connect your Gmail and Calendar after login for full AI capability. You can do this anytime.
          </p>
        </div>
      </article>
    </div>
  )
}
