/**
 * WelcomePage (stage 6c): first-run onboarding. Verifies the honest framing
 * (what this is / is NOT), the literal privacy summary (design §5.6), the
 * TextReel headline in both motion modes via EffectsContext, the GlassOrb
 * hero (lib vs static frosted fallback), and the CTA contract: sets
 * `reframe:onboarded` and navigates to /chat.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { EffectsProvider } from '../effects/EffectsContext'
import { setMediaQuery } from '../test/setup'
import { WelcomePage } from './WelcomePage'

vi.mock('@samasante/liquid-glass', () => ({
  Glass: ({ children }: { children?: ReactNode }) => (
    <div data-testid="mock-glass">{children}</div>
  ),
}))

const REDUCED_QUERY = '(prefers-reduced-motion: reduce)'
const ONBOARDED_KEY = 'reframe:onboarded'

function renderWelcome() {
  return render(
    <MemoryRouter initialEntries={['/welcome']}>
      <EffectsProvider>
        <Routes>
          <Route path="/welcome" element={<WelcomePage />} />
          <Route path="/chat" element={<h1>Chat destination</h1>} />
        </Routes>
      </EffectsProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  window.localStorage.removeItem(ONBOARDED_KEY)
})

describe('WelcomePage — honest framing', () => {
  it('says what this IS: wellness support, paced exercises, check-ins', () => {
    renderWelcome()

    expect(screen.getByRole('heading', { name: 'What this is' })).toBeInTheDocument()
    expect(screen.getByText(/wellness support/i)).toBeInTheDocument()
    expect(screen.getByText(/looping thoughts/i)).toBeInTheDocument()
    expect(screen.getByText(/difficult memories/i)).toBeInTheDocument()
    expect(screen.getByText(/self-criticism/i)).toBeInTheDocument()
    expect(screen.getByText(/paced exercises/i)).toBeInTheDocument()
    expect(
      screen.getByText(/and check-ins to notice how you're doing/i),
    ).toBeInTheDocument()
  })

  it('says what this is NOT: not medical care, no condition-naming, not emergency support', () => {
    renderWelcome()

    expect(
      screen.getByRole('heading', { name: /what this is not/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/not medical care/i)).toBeInTheDocument()
    // Lane-clean honest framing: it cannot tell you what condition you have.
    expect(screen.getByText(/cannot tell you what condition/i)).toBeInTheDocument()
    expect(screen.getByText(/not emergency support/i)).toBeInTheDocument()
    // The crisis promise is concrete: real resources appear immediately.
    expect(screen.getByText(/real (crisis )?resources/i)).toBeInTheDocument()
  })
})

describe('WelcomePage — privacy summary (literal, design §5.6)', () => {
  it('states the three privacy facts plainly', () => {
    renderWelcome()

    expect(screen.getByRole('heading', { name: /your privacy/i })).toBeInTheDocument()
    expect(
      screen.getByText(/messages (go to|are sent to) the configured AI only when/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/journal stays on this device/i)).toBeInTheDocument()
    expect(
      screen.getByText(/check-ins are stored locally/i),
    ).toBeInTheDocument()
  })
})

describe('WelcomePage — TextReel headline', () => {
  it('renders the TextReel headline element (motion mode still shows a heading immediately)', () => {
    renderWelcome()

    // The h1 exists from the first paint (intermediate word), so the page
    // never looks broken while the reel runs; the settle behavior itself is
    // covered in TextReel.test.tsx.
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    expect(screen.getByTestId('text-reel')).toBeInTheDocument()
  })

  it('renders the final headline statically under reduced motion', () => {
    setMediaQuery(REDUCED_QUERY, true)
    renderWelcome()

    const reel = screen.getByTestId('text-reel')
    expect(reel).toHaveTextContent('A calmer way to begin.')
    // No per-word churn: the static marker is set.
    expect(reel).toHaveAttribute('data-static', 'true')
  })
})

describe('WelcomePage — GlassOrb hero', () => {
  it('renders the orb, mounting the glass lib when motion is allowed', () => {
    renderWelcome()

    expect(screen.getByTestId('glass-orb')).toBeInTheDocument()
    expect(screen.getByTestId('mock-glass')).toBeInTheDocument()
  })

  it('renders the static frosted fallback under reduced motion', () => {
    setMediaQuery(REDUCED_QUERY, true)
    renderWelcome()

    const orb = screen.getByTestId('glass-orb')
    expect(orb).toHaveAttribute('data-fallback', 'frosted')
    expect(screen.queryByTestId('mock-glass')).not.toBeInTheDocument()
  })
})

describe('WelcomePage — Get started CTA', () => {
  it('sets the onboarded flag and navigates to /chat', async () => {
    const user = userEvent.setup()
    renderWelcome()

    await user.click(screen.getByRole('button', { name: 'Get started' }))

    expect(window.localStorage.getItem(ONBOARDED_KEY)).toBe('1')
    expect(await screen.findByText('Chat destination')).toBeInTheDocument()
  })

  it('works from the keyboard alone', async () => {
    const user = userEvent.setup()
    renderWelcome()

    // Tab through the nav links (5) to reach the CTA.
    for (let i = 0; i < 8; i += 1) {
      await user.tab()
      if (document.activeElement?.textContent === 'Get started') break
    }
    expect(screen.getByRole('button', { name: 'Get started' })).toHaveFocus()
    await user.keyboard('{Enter}')

    expect(window.localStorage.getItem(ONBOARDED_KEY)).toBe('1')
    expect(await screen.findByText('Chat destination')).toBeInTheDocument()
  })
})

describe('App — first-run redirect (never a gate)', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/')
  })

  it('redirects a first-run visitor on / to /welcome', async () => {
    render(<App />)

    await waitFor(() => expect(window.location.pathname).toBe('/welcome'))
    expect(screen.getByTestId('text-reel')).toBeInTheDocument()
  })

  it('leaves an already-onboarded visitor at / (which renders the welcome screen)', () => {
    window.localStorage.setItem(ONBOARDED_KEY, '1')

    render(<App />)

    expect(window.location.pathname).toBe('/')
    expect(screen.getByTestId('text-reel')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Get started' })).toBeInTheDocument()
  })

  it('never blocks deep links: /chat works on a first run', () => {
    window.history.pushState({}, '', '/chat')

    render(<App />)

    expect(window.location.pathname).toBe('/chat')
    expect(screen.getByRole('heading', { name: 'Chat', level: 1 })).toBeInTheDocument()
  })
})
