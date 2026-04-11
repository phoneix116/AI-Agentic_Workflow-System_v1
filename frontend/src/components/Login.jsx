import { useState, useEffect } from 'react'
import { apiRequest } from '../lib/apiClient'
import { ASSISTANT_NAME } from '../lib/branding'
import { normalizeOAuthResponse } from '../lib/apiResponse'

export default function Login({ onLoginSuccess, initialError = '', variant = 'page' }) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [oauthUrl, setOauthUrl] = useState(null)

  useEffect(() => {
    loadOAuthUrl()
  }, [])

  useEffect(() => {
    if (initialError) {
      setError(initialError)
    }
  }, [initialError])

  const loadOAuthUrl = async () => {
    try {
      const response = await apiRequest('/api/v1/auth/google/login')
      const oauthUrlValue = normalizeOAuthResponse(response)
      if (oauthUrlValue) {
        setOauthUrl(oauthUrlValue)
      } else {
        setError('Failed to generate login URL. Try refreshing.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load OAuth options. Try refreshing.')
    }
  }

  const handleGoogleLogin = () => {
    if (oauthUrl) {
      window.location.href = oauthUrl
    }
  }

  const isPanel = variant === 'panel'

  return (
    <div className={isPanel ? 'w-full' : 'min-h-screen bg-background-DEFAULT flex items-center justify-center p-4'}>
      {!isPanel && (
        <div
          aria-hidden="true"
          className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(69,162,158,0.2),_transparent_38%),radial-gradient(circle_at_bottom_right,_rgba(102,252,241,0.16),_transparent_45%)]"
        />
      )}

      <article
        className={
          isPanel
            ? 'glass relative z-10 w-full max-w-md rounded-[28px] border border-white/15 bg-[#1F2833]/85 p-7 shadow-[0_24px_68px_rgba(2,6,23,0.42)] md:p-9'
            : 'glass relative z-10 w-full max-w-md rounded-2xl border border-white/10 p-8 shadow-2xl md:p-12'
        }
      >
        <div className="text-center mb-8">
          <div
            className={
              isPanel
                ? 'mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[linear-gradient(145deg,#45A29E,#66FCF1)] shadow-[0_14px_34px_rgba(18,108,133,0.34)]'
                : 'h-16 w-16 mx-auto mb-4 rounded-2xl gradient-primary flex items-center justify-center shadow-glow'
            }
          >
            <span className="text-4xl font-bold text-white glow">🧠</span>
          </div>
          <h1 className={isPanel ? 'font-display mb-2 text-3xl font-semibold text-[#C5C6C7]' : 'text-3xl font-bold text-text-primary mb-2'}>
            {ASSISTANT_NAME}
          </h1>
          <p className={isPanel ? 'text-sm text-[#8E969F]' : 'text-sm text-text-secondary'}>
            Your Astra assistant for Email, Calendar & Tasks
          </p>
        </div>

        {error && (
          <div className="mb-6 rounded-lg border border-[#45A29E]/30 bg-[#45A29E]/10 p-4">
            <p className="text-sm text-[#B8FFFA]">{error}</p>
          </div>
        )}

        <div className="space-y-4 mb-6">
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={!oauthUrl || isLoading}
            className={
              isPanel
                ? 'w-full rounded-xl bg-[linear-gradient(145deg,#45A29E,#66FCF1)] px-4 py-3 font-semibold text-[#0B0C10] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_14px_30px_rgba(15,104,131,0.42)] disabled:opacity-50 disabled:hover:translate-y-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary'
                : 'w-full py-3 px-4 rounded-lg font-semibold text-[#0B0C10] gradient-primary hover:glow-lg hover:scale-105 disabled:opacity-50 disabled:scale-100 transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary'
            }
            aria-label="Sign in with Google"
          >
            {isLoading ? 'Signing in...' : '🔐 Sign in with Google'}
          </button>

          <p className={isPanel ? 'text-center text-xs text-[#8E969F]' : 'text-xs text-center text-text-tertiary'}>
            Sign in with Google to connect your Gmail, Calendar, and get full Astra assistance.
          </p>
        </div>

        <div
          className={
            isPanel
              ? 'rounded-xl border border-[#66FCF1]/30 bg-[#1F2833]/80 p-4 text-center'
              : 'rounded-lg border border-[#66FCF1]/30 bg-[#45A29E]/10 p-4 text-center'
          }
        >
          <p className={isPanel ? 'text-xs leading-relaxed text-[#C5C6C7]' : 'text-xs text-[#C5C6C7] leading-relaxed'}>
            💡 <span className="font-semibold">One-click login:</span> Sign in with Google to automatically connect your Gmail and Calendar for the best experience.
          </p>
        </div>
      </article>
    </div>
  )
}
