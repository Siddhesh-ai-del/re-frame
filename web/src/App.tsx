import { useEffect } from 'react'
import { BrowserRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { ToastProvider } from './components/toast/ToastProvider'
import { EffectsProvider } from './effects/EffectsContext'
import { AmbientBackground } from './effects/AmbientBackground'
import { FrostClouds } from './effects/FrostClouds'
import { ChatPage } from './pages/ChatPage'
import { CheckInsPage } from './pages/CheckInsPage'
import { ExercisesPage } from './pages/ExercisesPage'
import { SettingsPage } from './pages/SettingsPage'
import { WelcomePage, ONBOARDED_KEY } from './pages/WelcomePage'

/**
 * First-run redirect (stage 6c): a visitor who has never dismissed the
 * onboarding screen and lands on `/` is sent to `/welcome`. It is a
 * convenience, NEVER a gate — deep links (e.g. straight to /chat) work
 * regardless of the flag, and `/` itself still renders the welcome screen
 * for returning users who navigate back to it.
 */
function FirstRunRedirect() {
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    if (location.pathname !== '/') return
    let onboarded = false
    try {
      onboarded = window.localStorage.getItem(ONBOARDED_KEY) !== null
    } catch {
      // Storage unavailable: treat as onboarded — never trap the user.
      onboarded = true
    }
    if (!onboarded) navigate('/welcome', { replace: true })
  }, [location.pathname, navigate])

  return null
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <EffectsProvider>
          {/* Ambient layers (stage 6d): both render behind content
              (pointer-events-none, negative z-index) and are gated by the
              reduced-effects engine — the aurora statically, frost only on
              explicit opt-in. */}
          <AmbientBackground />
          <FrostClouds />
          <FirstRunRedirect />
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<WelcomePage />} />
              <Route path="/welcome" element={<WelcomePage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/exercises" element={<ExercisesPage />} />
              <Route path="/check-ins" element={<CheckInsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </EffectsProvider>
      </ToastProvider>
    </BrowserRouter>
  )
}
