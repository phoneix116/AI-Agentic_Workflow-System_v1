import { useEffect, useState } from 'react'
import { apiRequest } from '../lib/apiClient'
import Modal from './Modal'

const initialForm = {
  name: '',
  email: '',
  timezone: 'UTC',
  language: 'en',
  organization: '',
  role: '',
  communication_tone: 'professional',
  working_hours_start: '09:00',
  working_hours_end: '18:00',
  role_context: '',
  ai_instructions: '',
}

export default function UserProfileModal({ isOpen, onClose }) {
  const [formData, setFormData] = useState(initialForm)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    if (!isOpen) {
      return
    }

    let mounted = true

    const loadProfile = async () => {
      setLoading(true)
      setError('')
      setSuccess('')

      try {
        const response = await apiRequest('/api/v1/users/profile', { method: 'GET' })
        const profile = response?.profile

        if (!mounted || !profile) {
          return
        }

        setFormData({
          name: profile.name || '',
          email: profile.email || '',
          timezone: profile.timezone || 'UTC',
          language: profile.language || 'en',
          organization: profile.organization || '',
          role: profile.role || '',
          communication_tone: profile.communication_tone || 'professional',
          working_hours_start: profile.working_hours_start || '09:00',
          working_hours_end: profile.working_hours_end || '18:00',
          role_context: profile.role_context || '',
          ai_instructions: profile.ai_instructions || '',
        })
      } catch {
        if (mounted) {
          setError('Unable to load your profile right now.')
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    loadProfile()

    return () => {
      mounted = false
    }
  }, [isOpen])

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    setError('')
    setSuccess('')

    try {
      await apiRequest('/api/v1/users/profile', {
        method: 'PUT',
        body: JSON.stringify({
          name: formData.name,
          timezone: formData.timezone,
          language: formData.language,
          organization: formData.organization,
          role: formData.role,
          communication_tone: formData.communication_tone,
          working_hours_start: formData.working_hours_start,
          working_hours_end: formData.working_hours_end,
          role_context: formData.role_context,
          ai_instructions: formData.ai_instructions,
        }),
      })

      setSuccess('Profile updated. The assistant will now personalize tasks and events using this context.')
      window.dispatchEvent(new CustomEvent('assistant:profile-updated'))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save profile.'
      setError(message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="User Profile & AI Preferences">
      <div className="space-y-5">
        {loading ? (
          <p className="text-sm text-text-secondary">Loading your profile...</p>
        ) : (
          <>
            <p className="text-sm text-text-secondary">
              Update your role, organization, and AI guidance so generated tasks/events match your work context.
            </p>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Field label="Name" value={formData.name} onChange={(value) => handleInputChange('name', value)} />
              <Field label="Email" value={formData.email} disabled onChange={() => {}} />
              <Field label="Timezone" value={formData.timezone} onChange={(value) => handleInputChange('timezone', value)} />
              <Field label="Language" value={formData.language} onChange={(value) => handleInputChange('language', value)} />
              <Field label="Organization" value={formData.organization} onChange={(value) => handleInputChange('organization', value)} />
              <Field label="Role" value={formData.role} onChange={(value) => handleInputChange('role', value)} />
              <Field
                label="Working Hours Start"
                value={formData.working_hours_start}
                onChange={(value) => handleInputChange('working_hours_start', value)}
              />
              <Field
                label="Working Hours End"
                value={formData.working_hours_end}
                onChange={(value) => handleInputChange('working_hours_end', value)}
              />
              <Field
                label="Communication Tone"
                value={formData.communication_tone}
                onChange={(value) => handleInputChange('communication_tone', value)}
                placeholder="professional, concise, friendly"
              />
            </div>

            <TextArea
              label="Role Context"
              value={formData.role_context}
              onChange={(value) => handleInputChange('role_context', value)}
              placeholder="Describe your responsibilities, team scope, and decision style."
            />

            <TextArea
              label="AI Instructions"
              value={formData.ai_instructions}
              onChange={(value) => handleInputChange('ai_instructions', value)}
              placeholder="Tell the assistant how to structure task/event suggestions for your workflow."
            />

            {error && <Banner tone="error" text={error} />}
            {success && <Banner tone="success" text={success} />}

            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="
                touch-target w-full rounded-lg border border-secondary/40 bg-secondary/10 px-4 py-2.5
                text-sm font-semibold text-secondary transition-all duration-200
                hover:bg-secondary/20 disabled:cursor-not-allowed disabled:opacity-50
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary
              "
            >
              {saving ? 'Saving...' : 'Save Profile'}
            </button>
          </>
        )}
      </div>
    </Modal>
  )
}

function Field({ label, value, onChange, disabled = false, placeholder = '' }) {
  return (
    <label className="space-y-1">
      <span className="text-xs font-semibold text-text-secondary">{label}</span>
      <input
        type="text"
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        className="
          w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-text-primary
          placeholder:text-text-secondary disabled:cursor-not-allowed disabled:opacity-70
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary
        "
      />
    </label>
  )
}

function TextArea({ label, value, onChange, placeholder }) {
  return (
    <label className="space-y-1 block">
      <span className="text-xs font-semibold text-text-secondary">{label}</span>
      <textarea
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        rows={3}
        className="
          w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-text-primary
          placeholder:text-text-secondary focus-visible:outline-none focus-visible:ring-2
          focus-visible:ring-secondary resize-y
        "
      />
    </label>
  )
}

function Banner({ tone, text }) {
  const styles =
    tone === 'error'
      ? 'border-red-300/30 bg-red-500/10 text-red-200'
      : 'border-green-300/30 bg-green-500/10 text-green-200'

  return (
    <div className={`rounded-lg border px-3 py-2 text-sm ${styles}`}>
      {text}
    </div>
  )
}
