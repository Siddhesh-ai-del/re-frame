/**
 * CheckInsPage (stage 6d): the measurement dashboard.
 *
 * Covers the full state machine with the API client mocked wholesale: honest
 * loading/failure/retry for instruments AND history, the client-side
 * cross-instrument latest aggregate in the status bar, instrument switching,
 * the complete keyboard submission flow (PHQ-9, 9 items), the result +
 * toast + verbatim flag notices for all THREE routing tiers, all four
 * submission failure paths (never fake success), Done returning to history,
 * and the reduced-effects dataset contract.
 */
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ApiUnavailableError,
  BadRequestError,
  NetworkError,
  CHECKIN_BAD_REQUEST_MESSAGE,
  fetchCheckinHistory,
  fetchInstruments,
  fetchResources,
  submitCheckin,
} from '../api/client'
import { EffectsProvider } from '../effects/EffectsContext'
import { ToastProvider } from '../components/toast/ToastProvider'
import { CheckInsPage } from './CheckInsPage'
import type { components } from '../api/schema.d'

type InstrumentOut = components['schemas']['InstrumentOut']
type CheckInOut = components['schemas']['CheckInOut']
type ResourceOut = components['schemas']['ResourceOut']

vi.mock('../api/client', () => ({
  fetchInstruments: vi.fn(),
  fetchCheckinHistory: vi.fn(),
  submitCheckin: vi.fn(),
  fetchResources: vi.fn(),
  CHECKIN_BAD_REQUEST_MESSAGE: "Your check-in couldn't be sent. Please try again.",
  BadRequestError: class BadRequestError extends Error {
    constructor(message: string) {
      super(message)
      this.name = 'BadRequestError'
    }
  },
  ApiUnavailableError: class ApiUnavailableError extends Error {
    constructor(message = 'unavailable') {
      super(message)
      this.name = 'ApiUnavailableError'
    }
  },
  NetworkError: class NetworkError extends Error {
    constructor(message = 'offline') {
      super(message)
      this.name = 'NetworkError'
    }
  },
}))

const mockFetchInstruments = vi.mocked(fetchInstruments)
const mockFetchCheckinHistory = vi.mocked(fetchCheckinHistory)
const mockSubmitCheckin = vi.mocked(submitCheckin)
const mockFetchResources = vi.mocked(fetchResources)

/** The API's own scripted wording — asserted EXACTLY as returned (D9). */
const CONCERN_TEXT =
  'Thank you for taking the time to check in with us — what you shared matters, and it ' +
  'took real courage to notice how you have been feeling and to say it out loud. We are ' +
  'not able to judge or label what this means for you, and no score can capture the whole ' +
  'of your experience. Please consider talking with a qualified professional who can ' +
  'listen properly and walk alongside you with care. Reaching out for support is a ' +
  'genuine strength, not a weakness, and you deserve support that is thoughtful and ' +
  'unhurried.'

const CRISIS_TEXT =
  "I'm really sorry you're carrying this right now — you deserve support, and I want to be " +
  "honest: I'm a wellness companion, not a crisis service, so I can't help with a crisis " +
  'moment. Please reach out to people who can: the 988 Suicide & Crisis Lifeline (US) at ' +
  '988lifeline.org, or Find A Helpline (IASP global directory) at findahelpline.com to find ' +
  'a helpline in your country. If you might be in immediate danger, please contact your ' +
  'local emergency services or go to the nearest emergency department right now, and try ' +
  'not to be alone while you wait.'

const PHQ9: InstrumentOut = {
  id: 'phq9',
  title: 'Patient Health Questionnaire-9 (PHQ-9)',
  recall_period: 'the past 2 weeks',
  scale_min: 0,
  scale_max: 3,
  total_min: 0,
  total_max: 27,
  items: [
    { index: 1, prompt: 'Little interest or pleasure in doing things' },
    { index: 2, prompt: 'Feeling down, depressed, or hopeless' },
    { index: 3, prompt: 'Trouble falling or staying asleep, or sleeping too much' },
    { index: 4, prompt: 'Feeling tired or having little energy' },
    { index: 5, prompt: 'Poor appetite or overeating' },
    {
      index: 6,
      prompt:
        'Feeling bad about yourself — or that you are a failure or have let yourself or your family down',
    },
    {
      index: 7,
      prompt: 'Trouble concentrating on things, such as reading the newspaper or watching television',
    },
    {
      index: 8,
      prompt:
        'Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual',
    },
    {
      index: 9,
      prompt: 'Thoughts that you would be better off dead or of hurting yourself in some way',
    },
  ],
  answer_options: [
    { value: 0, label: 'Not at all' },
    { value: 1, label: 'Several days' },
    { value: 2, label: 'More than half the days' },
    { value: 3, label: 'Nearly every day' },
  ],
  severity_bands: [
    { label: 'minimal', lower: 0, upper: 4 },
    { label: 'mild', lower: 5, upper: 9 },
    { label: 'moderate', lower: 10, upper: 14 },
    { label: 'moderately severe', lower: 15, upper: 19 },
    { label: 'severe', lower: 20, upper: 27 },
  ],
  citation:
    'Kroenke, Spitzer & Williams 2001, Journal of General Internal Medicine (PHQ-9; free to use, no permission required)',
}

const GAD7: InstrumentOut = {
  id: 'gad7',
  title: 'Generalized Anxiety Disorder-7 (GAD-7)',
  recall_period: 'the past 2 weeks',
  scale_min: 0,
  scale_max: 3,
  total_min: 0,
  total_max: 21,
  items: [
    { index: 1, prompt: 'Feeling nervous, anxious, or on edge' },
    { index: 2, prompt: 'Not being able to stop or control worrying' },
    { index: 3, prompt: 'Worrying too much about different things' },
    { index: 4, prompt: 'Trouble relaxing' },
    { index: 5, prompt: "Being so restless that it's hard to sit still" },
    { index: 6, prompt: 'Becoming easily annoyed or irritable' },
    { index: 7, prompt: 'Feeling afraid, as if something awful might happen' },
  ],
  answer_options: PHQ9.answer_options,
  severity_bands: [
    { label: 'minimal', lower: 0, upper: 4 },
    { label: 'mild', lower: 5, upper: 9 },
    { label: 'moderate', lower: 10, upper: 14 },
    { label: 'severe', lower: 15, upper: 21 },
  ],
  citation: 'Spitzer, Kroenke, Williams & Löwe 2006',
}

function checkin(overrides: Partial<CheckInOut> = {}): CheckInOut {
  return {
    instrument_id: 'phq9',
    date: '2026-01-05',
    responses: Array.from({ length: 9 }, () => 0),
    total: 0,
    severity_label: 'minimal',
    flags: [],
    action: 'proceed',
    message_id: null,
    message: null,
    ...overrides,
  }
}

const SUBMITTED = checkin({ date: '2026-10-18' })

const RESOURCES: ResourceOut[] = [
  { name: 'Find A Helpline (IASP global directory)', url: 'https://findahelpline.com' },
  { name: '988 Suicide & Crisis Lifeline (US)', url: 'https://988lifeline.org' },
  {
    name: 'If you are in immediate danger, contact your local emergency services',
    url: null,
  },
]

function renderPage() {
  return render(
    <EffectsProvider>
      <ToastProvider>
        <CheckInsPage />
      </ToastProvider>
    </EffectsProvider>,
  )
}

function checkinForm() {
  return screen.getByRole('form', { name: /check-in/i })
}

/** Answer the first option of every item in the visible form. */
async function answerAll(
  user: ReturnType<typeof userEvent.setup>,
  value = 0,
) {
  const groups = within(checkinForm()).getAllByRole('group')
  for (const group of groups) {
    await user.click(within(group).getAllByRole('radio')[value]!)
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  mockFetchInstruments.mockResolvedValue([PHQ9, GAD7])
  mockFetchCheckinHistory.mockResolvedValue([])
  mockFetchResources.mockResolvedValue(RESOURCES)
  mockSubmitCheckin.mockResolvedValue(SUBMITTED)
})

describe('CheckInsPage — instruments and status bar', () => {
  it('auto-selects the first instrument and shows an honest empty status', async () => {
    renderPage()

    expect(await screen.findByRole('form', { name: /check-in/i })).toBeInTheDocument()
    const picker = screen.getByRole('button', { name: /Patient Health Questionnaire-9/ })
    expect(picker).toHaveAttribute('aria-pressed', 'true')
    expect(
      await screen.findByRole('region', { name: 'Dashboard status' }),
    ).toHaveTextContent('No check-ins yet.')
    expect(within(picker).getByText('the past 2 weeks')).toBeInTheDocument()
  })

  it('shows an honest instrument failure with a retry that refetches', async () => {
    const user = userEvent.setup()
    mockFetchInstruments
      .mockRejectedValueOnce(new ApiUnavailableError())
      .mockResolvedValueOnce([PHQ9])

    renderPage()

    expect(
      await screen.findByText(/instrument list couldn't be loaded/i),
    ).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('form', { name: /check-in/i })).toBeInTheDocument()
  })

  it('aggregates the latest check-in across instruments in the status bar', async () => {
    mockFetchCheckinHistory.mockImplementation(async (id: string) =>
      id === 'phq9'
        ? [checkin({ date: '2026-01-05' })]
        : [
            checkin({
              instrument_id: 'gad7',
              date: '2026-02-01',
              responses: Array.from({ length: 7 }, () => 2),
              total: 8,
              severity_label: 'mild',
            }),
          ],
    )

    renderPage()

    const region = await screen.findByRole('region', { name: 'Dashboard status' })
    await waitFor(() => expect(region).toHaveTextContent('2026-02-01'))
    expect(region).toHaveTextContent('Generalized Anxiety Disorder-7 (GAD-7)')
    expect(region).not.toHaveTextContent('2026-01-05')
  })

  it('shows an honest history failure (status + chart) and recovers on retry', async () => {
    const user = userEvent.setup()
    let failing = true
    mockFetchCheckinHistory.mockImplementation(async () => {
      if (failing) throw new ApiUnavailableError()
      return []
    })

    renderPage()

    expect(await screen.findByText(/your history couldn't be loaded/i)).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Dashboard status' })).toHaveTextContent(
      "couldn't be loaded",
    )

    failing = false
    await user.click(screen.getByRole('button', { name: /try again/i }))
    expect(
      await screen.findByText(/your first check-in will start your history/i),
    ).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Dashboard status' })).toHaveTextContent(
        'No check-ins yet.',
      ),
    )
  })

  it('switches the form when another instrument is selected', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByRole('form', { name: /check-in/i })

    await user.click(screen.getByRole('button', { name: /Generalized Anxiety Disorder-7/ }))

    expect(screen.getByRole('group', { name: /Feeling nervous, anxious/ })).toBeInTheDocument()
    expect(
      screen.queryByRole('group', { name: /Little interest or pleasure/ }),
    ).not.toBeInTheDocument()
  })
})

describe('CheckInsPage — submission flow', () => {
  it('completes the full PHQ-9 with the keyboard, submits, and shows result + toast + status', async () => {
    const user = userEvent.setup()
    renderPage()
    const form = await screen.findByRole('form', { name: /check-in/i })

    const groups = within(form).getAllByRole('group')
    expect(groups).toHaveLength(9)
    for (const group of groups) {
      within(group).getAllByRole('radio')[0]!.focus()
      await user.keyboard(' ')
    }

    const submit = screen.getByRole('button', { name: /save|submit|check-in/i })
    expect(submit).toBeEnabled()
    await user.click(submit)

    const result = await screen.findByRole('region', { name: /check-in result/i })
    expect(result).toHaveTextContent('0')
    expect(result).toHaveTextContent('minimal')
    expect(result).toHaveTextContent(PHQ9.citation)
    expect(await screen.findByText('Check-in saved.')).toBeInTheDocument()

    const status = screen.getByRole('region', { name: 'Dashboard status' })
    await waitFor(() => expect(status).toHaveTextContent('2026-10-18'))
    expect(status).toHaveTextContent('Patient Health Questionnaire-9 (PHQ-9)')
  })

  it('Done returns from the result to the form, with the new point in the history', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByRole('form', { name: /check-in/i })
    await answerAll(user)
    await user.click(screen.getByRole('button', { name: /save|submit|check-in/i }))

    await screen.findByRole('region', { name: /check-in result/i })
    await user.click(screen.getByRole('button', { name: /done/i }))

    expect(screen.getByRole('form', { name: /check-in/i })).toBeInTheDocument()
    expect(
      await screen.findByText('2026-10-18: 0 (minimal)', { selector: 'li' }),
    ).toBeInTheDocument()
  })

  it('renders the chart and ring for existing history', async () => {
    mockFetchCheckinHistory.mockResolvedValue([
      checkin({ date: '2026-01-05', total: 6, severity_label: 'mild' }),
      checkin({ date: '2026-01-12', total: 9, severity_label: 'moderate' }),
    ])

    renderPage()

    const items = await screen.findAllByRole('listitem', { hidden: true })
    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent('2026-01-05: 6 (mild)')
    expect(items[1]).toHaveTextContent('2026-01-12: 9 (moderate)')
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
    expect(screen.getByText('moderate')).toBeInTheDocument()
  })
})

describe('CheckInsPage — routing tiers (verbatim)', () => {
  it('proceed: result + toast only, no notice at all', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByRole('form', { name: /check-in/i })
    await answerAll(user)
    await user.click(screen.getByRole('button', { name: /save|submit|check-in/i }))

    await screen.findByRole('region', { name: /check-in result/i })
    expect(await screen.findByText('Check-in saved.')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByTestId('crisis-banner')).not.toBeInTheDocument()
  })

  it('human_review: the API message verbatim as a status above the result', async () => {
    const user = userEvent.setup()
    mockSubmitCheckin.mockResolvedValue(
      checkin({
        date: '2026-10-18',
        total: 16,
        severity_label: 'moderately severe',
        flags: ['CONCERN'],
        action: 'human_review',
        message_id: 'checkin_concern_v1',
        message: CONCERN_TEXT,
      }),
    )
    renderPage()
    await screen.findByRole('form', { name: /check-in/i })
    await answerAll(user)
    await user.click(screen.getByRole('button', { name: /save|submit|check-in/i }))

    const notice = await screen.findByText(CONCERN_TEXT)
    expect(notice.closest('[role="status"]')).not.toBeNull()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByTestId('crisis-banner')).not.toBeInTheDocument()
    expect(
      within(screen.getByRole('region', { name: /check-in result/i })).getByText('16'),
    ).toBeInTheDocument()
    expect(mockFetchResources).not.toHaveBeenCalled()
  })

  it('hard_bypass: verbatim crisis message as an alert with banner and resources, not toast-only', async () => {
    const user = userEvent.setup()
    mockSubmitCheckin.mockResolvedValue(
      checkin({
        date: '2026-10-18',
        total: 24,
        severity_label: 'severe',
        flags: ['ESCALATE'],
        action: 'hard_bypass',
        message_id: 'crisis_response_v1',
        message: CRISIS_TEXT,
      }),
    )
    renderPage()
    await screen.findByRole('form', { name: /check-in/i })
    await answerAll(user)
    await user.click(screen.getByRole('button', { name: /save|submit|check-in/i }))

    expect(await screen.findByText(CRISIS_TEXT)).toBeInTheDocument()
    expect(screen.getByTestId('crisis-banner')).toBeInTheDocument()
    expect(screen.getAllByRole('alert').length).toBeGreaterThan(0)
    await waitFor(() => expect(mockFetchResources).toHaveBeenCalled())
    expect(
      await screen.findByRole('link', { name: /Find A Helpline/ }),
    ).toHaveAttribute('href', 'https://findahelpline.com')
    // The success toast may coexist — escalation is never ONLY a toast (D9).
    expect(screen.getByText('Check-in saved.')).toBeInTheDocument()
  })
})

describe('CheckInsPage — submission failure paths (never fake success)', () => {
  const cases: Array<[string, () => unknown, RegExp]> = [
    ['a 422', () => new BadRequestError(CHECKIN_BAD_REQUEST_MESSAGE), /couldn't be sent/i],
    ['a 503', () => new ApiUnavailableError(), /service isn't responding|unavailable/i],
    ['a network failure', () => new NetworkError(), /offline|connection/i],
    ['an unknown error', () => new Error('boom'), /something went wrong|try again/i],
  ]

  for (const [name, makeError, pattern] of cases) {
    it(`shows an honest alert after ${name}, keeping the form and faking nothing`, async () => {
      const user = userEvent.setup()
      mockSubmitCheckin.mockRejectedValue(makeError())
      renderPage()
      await screen.findByRole('form', { name: /check-in/i })
      await answerAll(user)
      await user.click(screen.getByRole('button', { name: /save|submit|check-in/i }))

      const alert = await screen.findByRole('alert')
      expect(alert).toHaveTextContent(pattern)
      expect(screen.queryByRole('region', { name: /check-in result/i })).not.toBeInTheDocument()
      expect(screen.queryByText('Check-in saved.')).not.toBeInTheDocument()
      expect(screen.getByRole('form', { name: /check-in/i })).toBeInTheDocument()
    })
  }
})

describe('CheckInsPage — reduced-effects contract', () => {
  it('mirrors the resolved reduced-effects decision onto the html dataset', async () => {
    renderPage()
    await screen.findByRole('form', { name: /check-in/i })
    expect(document.documentElement.dataset.reducedEffects).toBe('false')
  })
})
