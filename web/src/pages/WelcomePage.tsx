/**
 * WelcomePage (stage 6c): first-run onboarding.
 *
 * Honest framing per design §4/§5: what this IS (wellness support for
 * looping thoughts, difficult memories, self-criticism; paced exercises;
 * check-ins) and what it is NOT (not medical care, cannot tell you what
 * condition you have, not emergency support — in a crisis the chat shows
 * real resources immediately). The privacy summary is literal (§5.6).
 *
 * The TextReel headline and the GlassOrb hero are the one usage sites for
 * those components. "Get started" sets `reframe:onboarded` and continues to
 * /chat — onboarding is never a gate (deep links work regardless).
 */
import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { GlassOrb } from '../components/onboarding/GlassOrb'
import { TextReel } from '../components/onboarding/TextReel'

/** LocalStorage key marking that the onboarding screen has been seen. */
export const ONBOARDED_KEY = 'reframe:onboarded'

const HEADLINE_WORDS = ['Pause', 'Notice', 'Breathe'] as const
const HEADLINE_FINAL = 'A calmer way to begin.'

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
      className="mx-auto flex w-full max-w-page flex-col gap-8 px-6 py-12"
    >
      <div className="flex flex-col items-center gap-6">
        <h1 className="text-2xl font-medium text-ink">Welcome</h1>
        <GlassOrb />
        <TextReel words={HEADLINE_WORDS} finalText={HEADLINE_FINAL} />
      </div>

      <div className="mx-auto flex w-full max-w-[720px] flex-col gap-4">
        <h2 className="text-xl font-medium text-ink">What this is</h2>
        <p className="text-ink">
          RE:FRAME is wellness support for looping thoughts, difficult
          memories, and self-criticism. It offers paced exercises you can try
          in a minute or two, and check-ins to notice how you're doing over
          time.
        </p>

        <h2 className="text-xl font-medium text-ink">What this is not</h2>
        <p className="text-ink">
          RE:FRAME is not medical care. It cannot tell you what condition you
          have. It is not emergency support: if you are in a crisis, the chat
          shows real crisis resources immediately.
        </p>

        <h2 className="text-xl font-medium text-ink">Your privacy</h2>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-ink">
          <li>
            Messages go to the configured AI only when it has been set up.
          </li>
          <li>Your journal stays on this device.</li>
          <li>Check-ins are stored locally in the app's own database.</li>
        </ul>

        <button
          type="button"
          onClick={getStarted}
          className="mt-2 self-start rounded-pill bg-accent px-6 py-3 text-sm text-bg transition-colors duration-150"
        >
          Get started
        </button>
      </div>
    </section>
  )
}
