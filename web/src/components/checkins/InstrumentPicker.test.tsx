/**
 * InstrumentPicker (stage 6d): choose which instrument to fill in, from
 * GET /instruments. Radio-style buttons showing title + recall period, with
 * honest loading and failure states (a retry that actually refetches).
 */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { InstrumentPicker } from './InstrumentPicker'
import type { components } from '../../api/schema.d'

type InstrumentOut = components['schemas']['InstrumentOut']

const PHQ9: InstrumentOut = {
  id: 'phq9',
  title: 'Patient Health Questionnaire-9 (PHQ-9)',
  recall_period: 'the past 2 weeks',
  scale_min: 0,
  scale_max: 3,
  total_min: 0,
  total_max: 27,
  items: [{ index: 1, prompt: 'Little interest or pleasure in doing things' }],
  answer_options: [{ value: 0, label: 'Not at all' }],
  severity_bands: [{ label: 'minimal', lower: 0, upper: 4 }],
  citation: 'Kroenke, Spitzer & Williams 2001',
}

const K10: InstrumentOut = {
  ...PHQ9,
  id: 'k10',
  title: 'Kessler Psychological Distress Scale (K-10)',
  recall_period: 'the past 30 days',
}

function renderPicker(
  props: Partial<React.ComponentProps<typeof InstrumentPicker>> = {},
) {
  const onSelect = vi.fn()
  const onRetry = vi.fn()
  render(
    <InstrumentPicker
      instruments={[PHQ9, K10]}
      loading={false}
      failed={false}
      selectedId="phq9"
      onSelect={onSelect}
      onRetry={onRetry}
      {...props}
    />,
  )
  return { onSelect, onRetry }
}

describe('InstrumentPicker', () => {
  it('lists every instrument with its title and recall period', () => {
    renderPicker()
    expect(
      screen.getByRole('button', { name: /Patient Health Questionnaire-9/ }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Kessler Psychological/ })).toBeInTheDocument()
    expect(screen.getAllByText('the past 2 weeks').length).toBeGreaterThan(0)
    expect(screen.getAllByText('the past 30 days').length).toBeGreaterThan(0)
  })

  it('marks the selected instrument with aria-pressed', () => {
    renderPicker()
    expect(
      screen.getByRole('button', { name: /Patient Health Questionnaire-9/ }),
    ).toHaveAttribute('aria-pressed', 'true')
    expect(
      screen.getByRole('button', { name: /Kessler Psychological/ }),
    ).toHaveAttribute('aria-pressed', 'false')
  })

  it('renders the selected chip with AA-safe accent text on the soft tint', () => {
    // Stage 6e a11y: accent text on `--accent-soft` is 4.19:1 (axe-flagged
    // on /check-ins); the selected state uses `text-accent-ink` instead.
    renderPicker()
    const selected = screen.getByRole('button', {
      name: /Patient Health Questionnaire-9/,
    })
    expect(selected.className).toContain('bg-accent-soft')
    expect(selected.className).toContain('text-accent-ink')
    expect(selected.className).not.toMatch(/(^|\s)text-accent(\s|$)/)
  })

  it('reports a selection with the instrument id', async () => {
    const user = userEvent.setup()
    const { onSelect } = renderPicker()

    await user.click(screen.getByRole('button', { name: /Kessler Psychological/ }))
    expect(onSelect).toHaveBeenCalledWith('k10')
  })

  it('announces an honest loading state', () => {
    renderPicker({ instruments: null, loading: true })
    expect(screen.getByRole('status')).toHaveTextContent('Loading instruments…')
  })

  it('shows an honest failure state with a retry that fires', async () => {
    const user = userEvent.setup()
    const { onRetry } = renderPicker({ instruments: null, failed: true })

    expect(screen.getByRole('status')).toHaveTextContent(
      "The instrument list couldn't be loaded right now.",
    )
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('failure wins over loading (never both, never a fake list)', () => {
    renderPicker({ instruments: null, loading: true, failed: true })
    expect(screen.getByRole('status')).toHaveTextContent("couldn't be loaded")
    expect(screen.queryByRole('button', { name: /Patient Health/ })).not.toBeInTheDocument()
  })
})
