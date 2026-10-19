/**
 * MessageBubble: user vs assistant variants, muted styling for the
 * human_review / filtered_fallback routes, and the "RE:FRAME" aria-label on
 * assistant bubbles. Violations are internal and never rendered.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MessageBubble } from './MessageBubble'

describe('MessageBubble', () => {
  it('renders the message text', () => {
    render(<MessageBubble role="user" text="I feel overwhelmed today" />)
    expect(screen.getByText('I feel overwhelmed today')).toBeInTheDocument()
  })

  it('marks the user variant on the right with the terracotta CTA gradient', () => {
    const { container } = render(
      <MessageBubble role="user" text="hello" />,
    )
    const bubble = container.querySelector('[data-variant="user"]')
    expect(bubble).not.toBeNull()
    expect(bubble!.className).toContain('self-end')
    // Stage 6f: light text over the axe-verified cta gradient stops.
    expect(bubble!.className).toContain('bubble-user')
    expect(bubble!.className).not.toContain('bg-accent-soft')
  })

  it('marks the assistant variant on the left with surface background', () => {
    const { container } = render(
      <MessageBubble role="assistant" text="hi there" route="generated" />,
    )
    const bubble = container.querySelector('[data-variant="assistant"]')
    expect(bubble).not.toBeNull()
    expect(bubble!.className).toContain('self-start')
    expect(bubble!.className).toContain('bg-surface')
  })

  it('labels the assistant bubble as RE:FRAME for assistive tech', () => {
    render(<MessageBubble role="assistant" text="hi" route="generated" />)
    expect(screen.getByLabelText('RE:FRAME')).toHaveTextContent('hi')
  })

  it.each(['human_review', 'filtered_fallback'] as const)(
    'uses the muted variant for route %s',
    (route) => {
      const { container } = render(
        <MessageBubble role="assistant" text="boundary copy" route={route} />,
      )
      const bubble = container.querySelector('[data-variant="muted"]')
      expect(bubble).not.toBeNull()
      expect(bubble!.className).toContain('text-ink-muted')
    },
  )

  it('uses the plain assistant variant for the generated and crisis routes', () => {
    for (const route of ['generated', 'crisis_bypass']) {
      const { container, unmount } = render(
        <MessageBubble role="assistant" text="reply" route={route} />,
      )
      expect(container.querySelector('[data-variant="assistant"]')).not.toBeNull()
      expect(container.querySelector('[data-variant="muted"]')).toBeNull()
      unmount()
    }
  })
})
