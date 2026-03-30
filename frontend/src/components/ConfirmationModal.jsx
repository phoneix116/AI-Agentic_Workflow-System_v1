import { useEffect } from 'react'

/**
 * Confirmation Dialog Component
 * Features: custom confirmation dialog with title, message, and action buttons
 * Accessibility: focus management, ARIA attributes
 */
export default function ConfirmationModal({ isOpen, onConfirm, onCancel, title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', isLoading = false, isDangerous = false }) {
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onCancel()
      }
    }

    window.addEventListener('keydown', handleEscape)
    document.body.style.overflow = 'hidden'

    return () => {
      window.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, onCancel])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-950/60 backdrop-blur-md animate-fade-in"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Modal Content */}
      <div className="relative z-10 w-full max-w-sm mx-4">
        <div className={`
          rounded-xl border shadow-2xl
          ${isDangerous 
            ? 'border-red-300/30 bg-red-500/10' 
            : 'border-white/10 bg-background-DEFAULT'
          }
        `}>
          {/* Header */}
          <div className="border-b border-white/10 px-6 py-4">
            <h2 className={`text-lg font-bold ${isDangerous ? 'text-red-200' : 'text-text-primary'}`}>
              {title}
            </h2>
          </div>

          {/* Body */}
          <div className="px-6 py-4">
            <p className="text-text-secondary text-sm">
              {message}
            </p>
          </div>

          {/* Footer */}
          <div className="flex gap-3 border-t border-white/10 px-6 py-4 justify-end">
            <button
              type="button"
              onClick={onCancel}
              disabled={isLoading}
              className="
                touch-target rounded-lg px-4 py-2 text-sm font-medium
                border border-white/15 bg-white/5 text-text-secondary
                hover:border-white/25 hover:bg-white/10
                disabled:opacity-50 transition-all duration-200
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary
              "
            >
              {cancelLabel}
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={isLoading}
              className={`
                touch-target rounded-lg px-4 py-2 text-sm font-medium
                transition-all duration-200 disabled:opacity-50
                focus-visible:outline-none focus-visible:ring-2
                ${isDangerous
                  ? 'border border-red-300/30 bg-red-500/20 text-red-200 hover:bg-red-500/30 focus-visible:ring-red-400'
                  : 'border border-green-300/30 bg-green-500/20 text-green-200 hover:bg-green-500/30 focus-visible:ring-green-400'
                }
              `}
            >
              {isLoading ? '...' : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
