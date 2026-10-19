/**
 * App shell + routing: one header/nav/main/footer frame over five routes,
 * keyboard-accessible nav links, and an active-route marker.
 */
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import App from '../App'

const NAV_LINKS: Array<{ name: string; href: string }> = [
  { name: 'Welcome', href: '/' },
  { name: 'Chat', href: '/chat' },
  { name: 'Exercises', href: '/exercises' },
  { name: 'Check-ins', href: '/check-ins' },
  { name: 'Settings', href: '/settings' },
]

describe('AppShell', () => {
  it('renders the wordmark, navigation, main region, and footer', () => {
    render(<App />)
    expect(
      screen.getByRole('banner', { name: 'RE:FRAME' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('navigation')).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('contentinfo')).toHaveTextContent(
      'RE:FRAME — wellness support, not medical care.',
    )
  })

  it('offers all five routes as navigation links with the right hrefs', () => {
    render(<App />)
    const nav = screen.getByRole('navigation')
    for (const { name, href } of NAV_LINKS) {
      const link = within(nav).getByRole('link', { name })
      expect(link).toHaveAttribute('href', href)
    }
  })

  it('marks the active route with aria-current="page"', async () => {
    const user = userEvent.setup()
    render(<App />)
    const nav = screen.getByRole('navigation')

    expect(
      within(nav).getByRole('link', { name: 'Welcome' }),
    ).toHaveAttribute('aria-current', 'page')

    await user.click(within(nav).getByRole('link', { name: 'Chat' }))
    expect(within(nav).getByRole('link', { name: 'Chat' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(
      within(nav).getByRole('link', { name: 'Welcome' }),
    ).not.toHaveAttribute('aria-current', 'page')
  })

  it('styles the active route with the AA-safe accent text on the soft tint', () => {
    // Stage 6e a11y: `--accent` on `--accent-soft` is 4.19:1 (axe-flagged);
    // the active state must use the derived `text-accent-ink` token instead.
    render(<App />)
    // Whichever route the shared jsdom location lands on, exactly one nav
    // link carries aria-current="page" — that is the one with the tint.
    const active = within(screen.getByRole('navigation')).getByRole('link', {
      current: 'page',
    })
    expect(active.className).toContain('bg-accent-soft')
    expect(active.className).toContain('text-accent-ink')
    expect(active.className).not.toMatch(/(^|\s)text-accent(\s|$)/)
  })

  it('navigates to /chat on click and renders the Chat heading', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('link', { name: 'Chat' }))
    expect(screen.getByRole('heading', { name: 'Chat' })).toBeInTheDocument()
  })

  it.each([
    'Welcome',
    'Chat',
    'Exercises',
    'Check-ins',
    'Settings',
  ])('renders the %s page with its heading', async (name) => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('link', { name }))
    expect(screen.getByRole('heading', { name, level: 1 })).toBeInTheDocument()
  })
})
