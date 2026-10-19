/**
 * WelcomePage (stage 6c/6f): first-run onboarding in the Golden Glass
 * direction (spec §5) — centered hero (orb + eyebrow + serif display h1 +
 * italic terracotta second line + gradient CTA) over three warm panel cards.
 *
 * Honest framing per design §4/§5: what this IS (wellness support for
 * looping thoughts, difficult memories, self-criticism; paced exercises;
 * check-ins) and what it is NOT (not medical care, cannot tell you what
 * condition you have, not emergency support — in a crisis the chat shows
 * real resources immediately). The privacy summary is literal (§5.6).
 * Copy is byte-identical to the sage era — the only NEW string is the
 * eyebrow the stage-6f spec sanctions.
 *
 * The TextReel headline and the GlassOrb hero are usage sites 2 (orb) for
 * the shared glass primitive. "Get started" sets `reframe:onboarded` and
 * continues to /chat — onboarding is never a gate (deep links work regardless).
 */
import { useCallback, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { GlassOrb } from '../components/onboarding/GlassOrb'
import { TextReel } from '../components/onboarding/TextReel'

/** LocalStorage key marking that the onboarding screen has been seen. */
export const ONBOARDED_KEY = 'reframe:onboarded'

const HEADLINE_WORDS = ['Pause', 'Notice', 'Breathe'] as const
const HEADLINE_FINAL = 'A calmer way to begin.'

/** Warm `--panel` card with an accent-dot uppercase heading (spec §5). */
function InfoCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="panel rounded-[var(--radius-card)] p-6">
      <h2 className="mb-3 flex items-center gap-2.5 text-xs font-extrabold uppercase tracking-[0.14em] text-accent-ink">
        <span
          aria-hidden="true"
          className="h-2.5 w-2.5 flex-none rounded-full bg-accent shadow-[0_0_0_3px_rgba(255,255,255,0.7)]"
        />
        {title}
      </h2>
      {children}
    </div>
  )
}

export function WelcomePage() {
  const navigate = useNavigate()

  const getStarted = useCallback(() => {
    try {
      window.localStorage.setItem(ONBOARDED_KEY, '1')
    } catch {
      // Storage unavailable: still let the user into the app.
    }
    navigate('/chat')
  }, [navigate])

  return (
    <section
      aria-label="Welcome"
      className="mx-auto flex w-full max-w-page flex-col gap-10 px-6 py-12"
    >
      <div className="flex flex-col items-center gap-4">
        <GlassOrb />
        <p className="text-xs font-extrabold uppercase tracking-[0.28em] text-accent-ink">
          A QUIET PLACE TO THINK
        </p>
        <h1 className="font-display text-center text-5xl font-bold leading-[1.09] tracking-[-0.015em] text-ink">
          Welcome
        </h1>
        <TextReel words={HEADLINE_WORDS} finalText={HEADLINE_FINAL} />
        <button
          type="button"
          onClick={getStarted}
          className="btn-cta mt-3 rounded-pill px-7 py-3.5 text-sm font-bold shadow-[0_12px_32px_rgba(168,80,28,0.35)] transition-colors duration-150"
        >
          Get started
        </button>
      </div>

      <div className="mx-auto flex w-full max-w-[720px] flex-col gap-4">
        <InfoCard title="What this is">
          <p className="text-ink">
            RE:FRAME is wellness support for looping thoughts, difficult
            memories, and self-criticism. It offers paced exercises you can try
            in a minute or two, and check-ins to notice how you're doing over
            time.
          </p>
        </InfoCard>

        <InfoCard title="What this is not">
          <p className="text-ink">
            RE:FRAME is not medical care. It cannot tell you what condition you
            have. It is not emergency support: if you are in a crisis, the chat
            shows real crisis resources immediately.
          </p>
        </InfoCard>

        <InfoCard title="Your privacy">
          <ul className="flex list-disc flex-col gap-1 pl-5 text-ink">
            <li>
              Messages go to the configured AI only when it has been set up.
            </li>
            <li>Your journal stays on this device.</li>
            <li>Check-ins are stored locally in the app's own database.</li>
          </ul>
        </InfoCard>
      </div>
    </section>
  )
}
