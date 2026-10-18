import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { ToastProvider } from './components/toast/ToastProvider'
import { EffectsProvider } from './effects/EffectsContext'
import { ChatPage } from './pages/ChatPage'
import { CheckInsPage } from './pages/CheckInsPage'
import { ExercisesPage } from './pages/ExercisesPage'
import { SettingsPage } from './pages/SettingsPage'
import { WelcomePage } from './pages/WelcomePage'

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <EffectsProvider>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<WelcomePage />} />
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
