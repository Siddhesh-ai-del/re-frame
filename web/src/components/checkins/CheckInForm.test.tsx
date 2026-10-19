/**
 * CheckInForm (stage 6d): one radio group per item (fieldset/legend),
 * keyboard-complete selection, today's date pre-filled and shown, submit
 * gated on a full set of answers, an honest in-flight state, and the chat
 * pattern's honest error states (422/503/network/unknown — never fake
 * success). The client module is mocked wholesale: these tests drive UI
 * state transitions, not HTTP.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CheckInForm } from './CheckInForm'
import {
  submitCheckin,
  BadRequestError,
  ApiUnavailableError,
  NetworkError,
  CHECKIN_BAD_REQUEST_MESSAGE,
} from '../../api/client'
import type { components } from '../../api/schema.d'

type InstrumentOut = components['schemas']['InstrumentOut']
type CheckInOut = components['schemas']['CheckInOut']

vi.mock('../../api/client', () => ({
  submitCheckin: vi.fn(),
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

const submitCheckinMock = vi.mocked(submitCheckin)

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
  ],
  answer_options: [
    { value: 0, label: 'Not at all' },
    { value: 1, label: 'Several days' },
    { value: 2, label: 'More than half the days' },
    { value: 3, label: 'Nearly every day' },
  ],
  severity_bands: [{ label: 'minimal', lower: 0, upper: 4 }],
  citation: 'Kroenke, Spitzer & Williams 2001',
}

const RECORDED: CheckInOut = {
  instrument_id: 'phq9',
  date: '2026-10-18',
  responses: [0, 1, 3, 0, 0],
  total: 4,
  severity_label: 'minimal',
  flags: [],
  action: 'proceed',
  message_id: null,
  message: null,
}

function renderForm(overrides: Partial<React.ComponentProps<typeof CheckInForm>> = {}) {
  const onDone = vi.fn()
  render(<CheckInForm instrument={PHQ9} onDone={onDone} {...overrides} />)
  return { onDone }
}

function submitButton() {
  return screen.getByRole('button', { name: /save|submit|check-in/i })
}

/**
 * The first still-unanswered radio for each unanswered item, in DOM order
 * (one representative radio per item — clicking it answers that item).
 */
function remainingRadios(): HTMLElement[] {
  return screen
    .getAllByRole('group')
    .map((group) => within(group).getAllByRole('radio')[0]!)
    .filter((radio) => !(radio as HTMLInputElement).checked)
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('CheckInForm structure', () => {
  it('renders one fieldset with a legend per item', () => {
    renderForm()

    expect(screen.getByRole('form', { name: /check-in/i })).toBeInTheDocument()

    const groups = screen.getAllByRole('group')
    expect(groups).toHaveLength(PHQ9.items.length)
    expect(screen.getByRole('group', { name: /Little interest or pleasure/ })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: /Feeling down, depressed/ })).toBeInTheDocument()
  })

  it('renders one radio per answer option per item', () => {
    renderForm()

    const radios = screen.getAllByRole('radio')
    expect(radios).toHaveLength(PHQ9.items.length * PHQ9.answer_options.length)
    expect(screen.getAllByLabelText('Not at all')).toHaveLength(PHQ9.items.length)
    expect(screen.getAllByLabelText('Nearly every day')).toHaveLength(PHQ9.items.length)
  })

  it("shows today's date as an ISO date", () => {
    renderForm()
    expect(screen.getByText(/^\d{4}-\d{2}-\d{2}$/)).toBeInTheDocument()
  })
})

describe('CheckInForm submission gating', () => {
  it('keeps submit disabled until every item is answered', async () => {
    const user = userEvent.setup()
    renderForm()

    expect(submitButton()).toBeDisabled()

    for (let item = 0; item < PHQ9.items.length; item += 1) {
      // Still disabled while at least one item remains unanswered…
      expect(submitButton()).toBeDisabled()
      await user.click(remainingRadios()[0]!)
    }

    expect(submitButton()).toBeEnabled()
  })

  it('submits responses in item order once every item is answered', async () => {
    const user = userEvent.setup()
    submitCheckinMock.mockResolvedValue(RECORDED)
    const { onDone } = renderForm()

    const picks = [0, 1, 3, 0, 0]
    for (let item = 0; item < picks.length; item += 1) {
      const options = within(screen.getAllByRole('group')[item]!).getAllByRole('radio')
      await user.click(options[picks[item]!]!)
    }
    await user.click(submitButton())

    await waitFor(() => expect(onDone).toHaveBeenCalledWith(RECORDED))
    expect(submitCheckinMock).toHaveBeenCalledTimes(1)
    const request = submitCheckinMock.mock.calls[0]![0]
    expect(request.instrument_id).toBe('phq9')
    expect(request.date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(request.responses).toEqual([0, 1, 3, 0, 0])
  })

  it('shows an honest submitting state while the request is in flight', async () => {
    const user = userEvent.setup()
    let resolveSubmit: (value: CheckInOut) => void = () => {}
    submitCheckinMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSubmit = resolve
        }),
    )
    renderForm()

    for (let item = 0; item < PHQ9.items.length; item += 1) {
      await user.click(remainingRadios()[0]!)
    }
    await user.click(submitButton())

    expect(await screen.findByText('Sending your check-in…')).toBeInTheDocument()
    expect(submitButton()).toBeDisabled()

    resolveSubmit(RECORDED)
    await waitFor(() =>
      expect(screen.queryByText('Sending your check-in…')).not.toBeInTheDocument(),
    )
  })
})

describe('CheckInForm keyboard completion', () => {
  it('selects the focused option with Space', () => {
    renderForm()
    const first = screen.getAllByLabelText('Not at all')[0] as HTMLInputElement
    first.focus()
    fireEvent.keyDown(first, { key: ' ' })
    expect(first.checked).toBe(true)
  })

  it('moves within a group with ArrowDown and ArrowUp', () => {
    renderForm()
    const group = screen.getAllByRole('radio').slice(0, PHQ9.answer_options.length)
    ;(group[0] as HTMLInputElement).focus()

    fireEvent.keyDown(group[0]!, { key: 'ArrowDown' })
    expect((group[1] as HTMLInputElement).checked).toBe(true)
    expect(document.activeElement).toBe(group[1])

    fireEvent.keyDown(group[1]!, { key: 'ArrowUp' })
    expect((group[0] as HTMLInputElement).checked).toBe(true)
    expect(document.activeElement).toBe(group[0])
  })

  it('completes every item with the keyboard alone, then submits', async () => {
    const user = userEvent.setup()
    submitCheckinMock.mockResolvedValue(RECORDED)
    const { onDone } = renderForm()

    for (let item = 0; item < PHQ9.items.length; item += 1) {
      const group = screen.getAllByRole('group')[item]!
      within(group).getAllByRole('radio')[0]!.focus()
      await user.keyboard(' ')
    }

    expect(submitButton()).toBeEnabled()
    await user.keyboard('{Enter}')
    await waitFor(() => expect(onDone).toHaveBeenCalledWith(RECORDED))
  })
})

describe('CheckInForm error notices', () => {
  async function answerAllAndSubmit(user: ReturnType<typeof userEvent.setup>) {
    for (let item = 0; item < PHQ9.items.length; item += 1) {
      await user.click(remainingRadios()[0]!)
    }
    await user.click(submitButton())
  }

  it('shows the 422 copy verbatim in an alert', async () => {
    const user = userEvent.setup()
    submitCheckinMock.mockRejectedValue(new BadRequestError(CHECKIN_BAD_REQUEST_MESSAGE))
    renderForm()
    await answerAllAndSubmit(user)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(CHECKIN_BAD_REQUEST_MESSAGE)
  })

  it('shows a check-in-specific notice for a 503', async () => {
    const user = userEvent.setup()
    submitCheckinMock.mockRejectedValue(new ApiUnavailableError())
    renderForm()
    await answerAllAndSubmit(user)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/service/i)
    expect(alert).toHaveTextContent(/try again/i)
  })

  it('keeps the answers visible after a network failure', async () => {
    const user = userEvent.setup()
    submitCheckinMock.mockRejectedValue(new NetworkError())
    renderForm()
    await answerAllAndSubmit(user)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/connection|offline|reachable/i)
    const radios = screen.getAllByRole('radio')
    expect(radios).toHaveLength(PHQ9.items.length * PHQ9.answer_options.length)
    expect(radios.some((radio) => (radio as HTMLInputElement).checked)).toBe(true)
  })

  it('shows a generic notice for an unknown error', async () => {
    const user = userEvent.setup()
    submitCheckinMock.mockRejectedValue(new Error('boom'))
    renderForm()
    await answerAllAndSubmit(user)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/something went wrong|try again/i)
  })
})
