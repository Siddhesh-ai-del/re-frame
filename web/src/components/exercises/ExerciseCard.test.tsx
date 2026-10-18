/**
 * ExerciseCard (stage 6c): one library module rendered honestly — title,
 * summary, numbered steps, the evidence tier as a LABEL ONLY (no risk
 * coloring, NICE NG225), sources as plain noopener/noreferrer links when
 * they are URLs, and contraindications surfaced verbatim when present.
 */
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ExerciseCard } from './ExerciseCard'
import type { components } from '../../api/schema.d'

type ExerciseOut = components['schemas']['ExerciseOut']

const EXERCISE: ExerciseOut = {
  id: 'rumination-postponement',
  title: 'Thought postponement',
  summary: 'Set aside a short, fixed window for the looping thoughts.',
  category: 'rumination',
  tier: 'A',
  steps: ['Notice the loop.', 'Park it for later.', 'Return to what you were doing.'],
  sources: ['Stenzel et al. 2025, Psychological Medicine'],
  contraindications: [],
  early_worsening_notice: true,
}

describe('ExerciseCard', () => {
  it('renders the title, summary, and numbered steps', () => {
    render(<ExerciseCard exercise={EXERCISE} />)

    expect(
      screen.getByRole('heading', { name: 'Thought postponement' }),
    ).toBeInTheDocument()
    expect(screen.getByText(EXERCISE.summary)).toBeInTheDocument()
    const steps = screen.getByRole('list', { name: /steps/i })
    const items = within(steps).getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(items[0]).toHaveTextContent('Notice the loop.')
  })

  it('shows the evidence tier as an honest label with no risk coloring', () => {
    const { container } = render(<ExerciseCard exercise={EXERCISE} />)

    expect(screen.getByText('Evidence tier: A')).toBeInTheDocument()
    // No traffic-light classes anywhere on the card (NICE NG225).
    expect(container.innerHTML).not.toMatch(/text-(red|green|yellow)-/)
  })

  it('renders a URL source as a noopener/noreferrer link', () => {
    render(
      <ExerciseCard
        exercise={{
          ...EXERCISE,
          sources: ['https://example.org/study', 'Stenzel et al. 2025'],
        }}
      />,
    )

    const link = screen.getByRole('link', { name: 'https://example.org/study' })
    expect(link).toHaveAttribute('href', 'https://example.org/study')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    // Non-URL citations render as plain text, not links.
    expect(screen.getByText('Stenzel et al. 2025')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Stenzel et al. 2025' })).not.toBeInTheDocument()
  })

  it('surfaces contraindications verbatim when present, hides the section otherwise', () => {
    const { rerender } = render(<ExerciseCard exercise={EXERCISE} />)
    expect(screen.queryByText(/keep in mind/i)).not.toBeInTheDocument()

    rerender(
      <ExerciseCard
        exercise={{ ...EXERCISE, contraindications: ['Skip this if it feels like too much.'] }}
      />,
    )
    expect(screen.getByText('Skip this if it feels like too much.')).toBeInTheDocument()
  })
})
