/**
 * TrendChart (stage 6d): a hand-rolled SVG polyline of `total` over `date`
 * for the selected instrument (no chart library). Accessibility contract: an
 * aria-label on the SVG plus a visually-hidden equivalent list of
 * "date: total (label)" entries; every point focusable. Tone contract: ink /
 * ink-muted / accent only — worsening must NEVER turn red
 * (docs/webapp-design.md §3 row 4). Honest loading/failure/empty states.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TrendChart } from './TrendChart'
import type { components } from '../../api/schema.d'

type CheckInOut = components['schemas']['CheckInOut']

function entry(overrides: Partial<CheckInOut> = {}): CheckInOut {
  return {
    instrument_id: 'phq9',
    date: '2026-01-05',
    responses: [1, 1, 1, 1, 0, 1, 0, 0, 1],
    total: 6,
    severity_label: 'mild',
    flags: [],
    action: 'proceed',
    message_id: null,
    message: null,
    ...overrides,
  }
}

function renderChart(
  entries: CheckInOut[],
  overrides: Partial<React.ComponentProps<typeof TrendChart>> = {},
) {
  const onRetry = vi.fn()
  const view = render(
    <TrendChart
      entries={entries}
      totalMin={0}
      totalMax={27}
      loading={false}
      failed={false}
      onRetry={onRetry}
      {...overrides}
    />,
  )
  return { onRetry, ...view }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('TrendChart states', () => {
  it('shows a loading state', () => {
    renderChart([], { loading: true })
    expect(screen.getByText(/loading your history/i)).toBeInTheDocument()
  })

  it('shows a failure state with a retry control that fires', async () => {
    const user = userEvent.setup()
    const { onRetry } = renderChart([], { failed: true })

    expect(screen.getByText(/your history couldn't be loaded/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /try again|retry/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('shows the empty-history message when there are no entries', () => {
    renderChart([])
    expect(
      screen.getByText(/your first check-in will start your history/i),
    ).toBeInTheDocument()
  })

  it('renders a chart with an equivalent hidden list of entries', () => {
    const entries = [
      entry({ date: '2026-01-05', total: 6, severity_label: 'mild' }),
      entry({ date: '2026-01-12', total: 9, severity_label: 'moderate' }),
    ]
    const { container } = renderChart(entries)

    expect(container.querySelector('svg')).not.toBeNull()

    const items = screen.getAllByRole('listitem', { hidden: true })
    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent('2026-01-05: 6 (mild)')
    expect(items[1]).toHaveTextContent('2026-01-12: 9 (moderate)')
  })

  it('labels the chart SVG for assistive technology', () => {
    const { container } = renderChart([entry()])
    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('aria-label')).toBeTruthy()
  })

  it('makes every data point focusable with its value announced', () => {
    renderChart([entry({ date: '2026-01-05', total: 6, severity_label: 'mild' })])

    const point = screen.getByRole('button', { name: /2026-01-05.*6/i })
    expect(point).toHaveAttribute('tabindex', '0')
    point.focus()
    expect(point).toHaveFocus()
  })

  it('renders the history in oldest-to-newest order', () => {
    const entries = [
      entry({ date: '2026-01-05', total: 6, severity_label: 'mild' }),
      entry({ date: '2026-01-12', total: 9, severity_label: 'moderate' }),
    ]
    renderChart(entries)
    const items = screen.getAllByRole('listitem', { hidden: true })
    expect(items[0]).toHaveTextContent('2026-01-05')
    expect(items[1]).toHaveTextContent('2026-01-12')
  })

  it('never colors points as risk', () => {
    const { container } = renderChart([
      entry({ total: 22, severity_label: 'severe', flags: ['ESCALATE'] }),
    ])
    for (const el of Array.from(container.querySelectorAll('*'))) {
      const className = typeof el.className === 'string' ? el.className : ''
      expect(className).not.toMatch(/(red|rose|crisis|warning|danger)/i)
    }
  })

  it('accepts a focus via keyboard on a data point', () => {
    renderChart([entry({ date: '2026-01-05', total: 6, severity_label: 'mild' })])
    const point = screen.getByRole('button', { name: /2026-01-05.*6/i })
    // fireEvent.focus dispatches the event but does NOT move jsdom's
    // activeElement; a direct focus() models what the browser does when
    // Tab lands on the tabindex="0" point.
    point.focus()
    expect(point).toHaveFocus()
  })
})
