import { BookOpen, ClipboardCheck, Home, MessageCircle, Settings, type LucideIcon } from 'lucide-react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { GlassSurface } from './glass/GlassSurface'

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
 * Application frame: a floating liquid-glass nav pill (lens site 1 of 3 —
 * spec §4), a main outlet, and the standing honesty disclaimer in the
 * footer. The Welcome item covers both `/` and the `/welcome` onboarding
 * route (stage 6c); every active link gets `aria-current="page"` and renders
 * as an ember ink pill.
 *
 * Landmark contract is unchanged: header keeps its `aria-label` (banner
 * role), nav keeps `aria-label="Primary"`.
 */
export function AppShell() {
  const { pathname } = useLocation()
  const isActive = (to: string) =>
    to === '/'
      ? pathname === '/' || pathname === '/welcome'
      : pathname === to

  // No bg on the root wrapper (stage 6d/6f): the AmbientBackground landscape
  // sits directly on the <html> background; a solid bg here would cover it.
  return (
    <div className="flex min-h-screen flex-col text-ink">
      <header aria-label="RE:FRAME" className="pb-2 pt-5">
        <GlassSurface
          variant="nav"
          className="mx-auto w-[calc(100%-40px)] max-w-[920px] shadow-[var(--shadow-soft)]"
        >
          <span className="flex items-center gap-2.5 text-base font-extrabold tracking-tight text-ink">
            <span
              aria-hidden="true"
              className="h-[26px] w-[26px] flex-none rounded-full shadow-[0_2px_8px_rgba(200,130,40,0.5)]"
              style={{
                background:
                  'radial-gradient(circle at 35% 30%, #FFF2D6, #F5A623 72%, #A8501C)',
              }}
            />
            RE:FRAME
          </span>
          <nav aria-label="Primary" className="flex flex-wrap items-center gap-0.5">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
              const active = isActive(to)
              return (
                <Link
                  key={to}
                  to={to}
                  aria-current={active ? 'page' : undefined}
                  className={[
                    'flex items-center gap-2 rounded-pill px-3 py-2 text-sm font-semibold transition-colors duration-150',
                    active
                      ? 'bg-ink text-ink-on shadow-[0_4px_14px_rgba(52,38,26,0.3)]'
                      : 'text-ink-muted hover:bg-white/55 hover:text-ink',
                  ].join(' ')}
                >
                  <Icon aria-hidden="true" size={16} />
                  <span>{label}</span>
                </Link>
              )
            })}
          </nav>
        </GlassSurface>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer aria-label="About" className="py-6">
        {/* `text-ink`, not `text-ink-muted`: the footer always sits over the
           landscape's hills (#AFC7A4 band) — muted measures 3.66:1 there
           (axe-flagged), ink is 8:1 on every backdrop layer. */}
        <p className="mx-auto w-full max-w-page px-6 text-sm text-ink">
          RE:FRAME — wellness support, not medical care.
        </p>
      </footer>
    </div>
  )
}
