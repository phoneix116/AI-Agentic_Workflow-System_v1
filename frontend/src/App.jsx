import { useState, useEffect } from 'react'
import Layout from './components/Layout'
import Login from './components/Login'

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)

  useEffect(() => {
    checkAuthentication()
  }, [])

  const checkAuthentication = () => {
    const token = window.localStorage.getItem('ai_assistant_token')
    setIsAuthenticated(!!token)
    setIsCheckingAuth(false)
  }

  const handleLoginSuccess = () => {
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    window.localStorage.removeItem('ai_assistant_token')
    setIsAuthenticated(false)
  }

  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-background-DEFAULT flex items-center justify-center">
        <div className="text-center">
          <div className="h-12 w-12 mx-auto mb-4 rounded-xl gradient-primary flex items-center justify-center animate-pulse">
            <span className="text-2xl">🧠</span>
          </div>
          <p className="text-text-secondary">Loading Astra...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />
  }

  return <Layout onLogout={handleLogout} />
}

