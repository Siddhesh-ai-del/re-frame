import { BookOpen, ClipboardCheck, Home, MessageCircle, Settings, type LucideIcon } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

const NAV_ITEMS: ReadonlyArray<{
  to: string
  label: string
  icon: LucideIcon
  end?: boolean
}> = [
  { to: '/', label: 'Welcome', icon: Home, end: true },
  { to: '/chat', label: 'Chat', icon: MessageCircle },
  { to: '/exercises', label: 'Exercises', icon: BookOpen },
  { to: '/check-ins', label: 'Check-ins', icon: ClipboardCheck },
  { to: '/settings', label: 'Settings', icon: Settings },
]

/**
 * Application frame: header with wordmark + primary nav, a main outlet, and
 * the standing honesty disclaimer in the footer. NavLink marks the active
 * route with `aria-current="page"` automatically.
 */
export function AppShell() {
  return (
    <div className="flex min-h-screen flex-col bg-bg text-ink">
      <header
        aria-label="RE:FRAME"
        className="border-b border-border bg-surface"
      >
        <div className="mx-auto flex w-full max-w-page items-center justify-between px-6 py-4">
          <span className="text-lg font-medium tracking-wide">RE:FRAME</span>
          <nav aria-label="Primary" className="flex gap-1">
            {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end ?? false}
                className={({ isActive }) =>
                  [
                    'flex items-center gap-2 rounded-pill px-3 py-2 text-sm transition-colors duration-150',
                    isActive
                      ? 'bg-accent-soft text-accent'
                      : 'text-ink-muted hover:bg-surface-sunk',
                  ].join(' ')
                }
              >
                <Icon aria-hidden="true" size={16} />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer
        aria-label="About"
        className="border-t border-border bg-surface py-6"
      >
        <p className="mx-auto w-full max-w-page px-6 text-sm text-ink-muted">
          RE:FRAME — wellness support, not medical care.
        </p>
      </footer>
    </div>
  )
}
