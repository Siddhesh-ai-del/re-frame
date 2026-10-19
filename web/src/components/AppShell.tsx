import { BookOpen, ClipboardCheck, Home, MessageCircle, Settings, type LucideIcon } from 'lucide-react'
import { Link, Outlet, useLocation } from 'react-router-dom'

const NAV_ITEMS: ReadonlyArray<{
  to: string
  label: string
  icon: LucideIcon
}> = [
  { to: '/', label: 'Welcome', icon: Home },
  { to: '/chat', label: 'Chat', icon: MessageCircle },
  { to: '/exercises', label: 'Exercises', icon: BookOpen },
  { to: '/check-ins', label: 'Check-ins', icon: ClipboardCheck },
  { to: '/settings', label: 'Settings', icon: Settings },
]

/**
 * Application frame: header with wordmark + primary nav, a main outlet, and
 * the standing honesty disclaimer in the footer. The Welcome item covers
 * both `/` and the `/welcome` onboarding route (stage 6c); every active
 * link gets `aria-current="page"`.
 */
export function AppShell() {
  const { pathname } = useLocation()
  const isActive = (to: string) =>
    to === '/'
      ? pathname === '/' || pathname === '/welcome'
      : pathname === to

  // No bg-bg on the root wrapper (stage 6d): the AmbientBackground aurora
  // sits directly on the <html> background; a solid bg here would cover it.
  return (
    <div className="flex min-h-screen flex-col text-ink">
      <header
        aria-label="RE:FRAME"
        className="border-b border-border bg-surface"
      >
        <div className="mx-auto flex w-full max-w-page items-center justify-between px-6 py-4">
          <span className="text-lg font-medium tracking-wide">RE:FRAME</span>
          <nav aria-label="Primary" className="flex gap-1">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
              const active = isActive(to)
              return (
                <Link
                  key={to}
                  to={to}
                  aria-current={active ? 'page' : undefined}
                  className={[
                    'flex items-center gap-2 rounded-pill px-3 py-2 text-sm transition-colors duration-150',
                    active
                      ? 'bg-accent-soft text-accent'
                      : 'text-ink-muted hover:bg-surface-sunk',
                  ].join(' ')}
                >
                  <Icon aria-hidden="true" size={16} />
                  <span>{label}</span>
                </Link>
              )
            })}
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
