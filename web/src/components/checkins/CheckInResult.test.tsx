/**
 * CheckInResult (stage 6d): the honest score screen. The total is the
 * instrument's own score with tabular numerals, the severity label is the
 * instrument's PUBLISHED wording, the citation is verbatim, and NO risk
 * coloring ever touches the score (docs/webapp-design.md §5.4, NG225 —
 * colors here are ink/accent only). A null severity label renders without a
 * fabricated placeholder.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CheckInResult } from './CheckInResult'
import type { components } from '../../api/schema.d'

type CheckInOut = components['schemas']['CheckInOut']
type InstrumentOut = components['schemas']['InstrumentOut']

const INSTRUMENT: InstrumentOut = {
  id: 'phq9',
  title: 'Patient Health Questionnaire-9 (PHQ-9)',
  recall_period: 'the past 2 weeks',
  scale_min: 0,
  scale_max: 3,
  total_min: 0,
  total_max: 27,
  items: [{ index: 1, prompt: 'Little interest or pleasure in doing things' }],
  answer_options: [{ value: 0, label: 'Not at all' }],
  severity_bands: [{ label: 'moderate', lower: 10, upper: 14 }],
  citation:
    'Kroenke, Spitzer & Williams 2001, Journal of General Internal Medicine (PHQ-9; free to use, no permission required)',
}

function baseResult(overrides: Partial<CheckInOut> = {}): CheckInOut {
  return {
    instrument_id: 'phq9',
    date: '2026-10-18',
    responses: [1, 2, 3, 2, 1, 1, 1, 1, 1],
    total: 13,
    severity_label: 'moderate',
    flags: [],
    action: 'proceed',
    message_id: null,
    message: null,
    ...overrides,
  }
}

function renderResult(overrides: Partial<CheckInOut> = {}) {
  const onDone = vi.fn()
  const view = render(
    <CheckInResult result={baseResult(overrides)} instrument={INSTRUMENT} onDone={onDone} />,
  )
  return { onDone, ...view }
}

describe('CheckInResult display', () => {
  it('renders the total with tabular numerals', () => {
    renderResult()
    const total = screen.getByText('13')
    expect(total).toBeInTheDocument()
    expect(total.className).toContain('tabular-nums')
  })

  it('renders the published severity label verbatim', () => {
    renderResult()
    expect(screen.getByText('moderate')).toBeInTheDocument()
  })

  it('renders the instrument citation verbatim', () => {
    renderResult()
    expect(
      screen.getByText(
        'Kroenke, Spitzer & Williams 2001, Journal of General Internal Medicine (PHQ-9; free to use, no permission required)',
      ),
    ).toBeInTheDocument()
  })

  it('renders a null severity label without a placeholder', () => {
    renderResult({ severity_label: null })
    expect(screen.queryByText(/unknown|n\/a|not available/i)).not.toBeInTheDocument()
    expect(screen.getByText('13')).toBeInTheDocument()
  })

  it('has a Done control that calls onDone', async () => {
    const user = userEvent.setup()
    const { onDone } = renderResult()
    await user.click(screen.getByRole('button', { name: /done/i }))
    expect(onDone).toHaveBeenCalledTimes(1)
  })
})

describe('CheckInResult tone', () => {
  const risky = [
    { name: 'a flagged result', overrides: { flags: ['CONCERN'], action: 'human_review' } },
    { name: 'a crisis-tier result', overrides: { flags: ['ESCALATE'], action: 'hard_bypass' } },
    { name: 'a severe band', overrides: { severity_label: 'severe', total: 24 } },
  ]

  for (const { name, overrides } of risky) {
    it(`does not color ${name} as risk`, () => {
      const { container } = renderResult(overrides)
      for (const el of Array.from(container.querySelectorAll('*'))) {
        const className = typeof el.className === 'string' ? el.className : ''
        expect(className).not.toMatch(/(red|rose|crisis|warning|danger)/i)
      }
    })
  }
})
