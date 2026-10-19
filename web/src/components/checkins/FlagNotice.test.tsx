/**
 * FlagNotice (stage 6d): the verbatim escalation layer above the result
 * (docs/webapp-design.md §5.2, D9). The API's `message` is presented EXACTLY
 * as returned — no re-wording, no paraphrase, no truncation. Styling and
 * semantics follow the routing action: proceed → nothing; human_review →
 * role="status" concern panel; hard_bypass → crisis treatment with
 * role="alert" plus always-visible support resources (escalation is never
 * toast-only).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { FlagNotice } from './FlagNotice'
import { fetchResources } from '../../api/client'
import type { components } from '../../api/schema.d'

type CheckInOut = components['schemas']['CheckInOut']
type ResourceOut = components['schemas']['ResourceOut']

vi.mock('../../api/client', () => ({
  fetchResources: vi.fn(),
}))

const fetchResourcesMock = vi.mocked(fetchResources)

/** The exact wording the mocked API returns — asserted verbatim below. */
const CONCERN_MESSAGE =
  'Thank you for taking the time to check in with us — what you shared matters, and it ' +
  'took real courage to notice how you have been feeling and to say it out loud.'

const CRISIS_MESSAGE =
  "I'm really sorry you're carrying this right now — you deserve support, and I want to be " +
  'honest: I am a wellness companion, not a crisis service.'

function resultWith(
  action: 'proceed' | 'human_review' | 'hard_bypass',
  message: string | null,
): CheckInOut {
  return {
    instrument_id: 'phq9',
    date: '2026-10-18',
    responses: Array.from({ length: 9 }, () => 3),
    total: 27,
    severity_label: 'severe',
    flags: action === 'proceed' ? [] : action === 'human_review' ? ['CONCERN'] : ['ESCALATE'],
    action,
    message_id: action === 'proceed' ? null : 'message',
    message,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('FlagNotice: proceed', () => {
  it('renders nothing even when a message is present', () => {
    const { container } = render(<FlagNotice result={resultWith('proceed', 'a stray message')} />)
    expect(container).toBeEmptyDOMElement()
    expect(fetchResourcesMock).not.toHaveBeenCalled()
  })
})

describe('FlagNotice: human_review', () => {
  it('renders the message verbatim as a status notice', () => {
    render(<FlagNotice result={resultWith('human_review', CONCERN_MESSAGE)} />)

    const status = screen.getByRole('status')
    expect(status).toHaveTextContent(CONCERN_MESSAGE)
    expect(fetchResourcesMock).not.toHaveBeenCalled()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByTestId('crisis-banner')).not.toBeInTheDocument()
  })
})

describe('FlagNotice: hard_bypass', () => {
  it('renders the message verbatim as an alert with crisis treatment', () => {
    render(<FlagNotice result={resultWith('hard_bypass', CRISIS_MESSAGE)} />)

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent(CRISIS_MESSAGE)
    expect(alert).toHaveTextContent(CRISIS_MESSAGE)
    // The verbatim message is the alert's own text, not a shortened version.
    expect(alert.textContent).toContain(CRISIS_MESSAGE)
  })

  it('fetches and shows support resources', async () => {
    const resources: ResourceOut[] = [
      { name: 'Find A Helpline (IASP global directory)', url: 'https://findahelpline.com' },
      { name: '988 Suicide & Crisis Lifeline (US)', url: 'https://988lifeline.org' },
      {
        name: 'If you are in immediate danger, contact your local emergency services',
        url: null,
      },
    ]
    fetchResourcesMock.mockResolvedValue(resources)
    render(<FlagNotice result={resultWith('hard_bypass', CRISIS_MESSAGE)} />)

    await waitFor(() => expect(fetchResourcesMock).toHaveBeenCalledTimes(1))
    expect(await screen.findByRole('link', { name: /Find A Helpline/ })).toHaveAttribute(
      'href',
      'https://findahelpline.com',
    )
    expect(screen.getByRole('link', { name: /988 Suicide/ })).toHaveAttribute(
      'href',
      'https://988lifeline.org',
    )
    expect(
      screen.getByText(/contact your local emergency services/i),
    ).toBeInTheDocument()
  })

  it('notes honestly when support resources could not be loaded', async () => {
    fetchResourcesMock.mockRejectedValue(new Error('down'))
    render(<FlagNotice result={resultWith('hard_bypass', CRISIS_MESSAGE)} />)

    expect(await screen.findByText(/support links couldn't load/i)).toBeInTheDocument()
    // The escalation itself never disappears with the resources.
    expect(screen.getByRole('alert')).toHaveTextContent(CRISIS_MESSAGE)
  })
})
