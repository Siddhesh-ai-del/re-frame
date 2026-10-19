/**
 * ChatPage state machine: empty state, happy path, pending, the crisis
 * escalation (sticky banner + resources), muted route variants, every honest
 * error path, and the offline/online toasts.
 *
 * The API client module is mocked wholesale so these tests exercise UI state
 * transitions, not HTTP.
 */
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ApiUnavailableError,
  BadRequestError,
  NetworkError,
  fetchResources,
  sendChat,
} from '../api/client'
import { EffectsProvider } from '../effects/EffectsContext'
import { ToastProvider } from '../components/toast/ToastProvider'
import { ChatPage } from './ChatPage'
import type { components } from '../api/schema.d'

// The empty-state GlassOrb and the composer lens both mount the glass lib
// when motion is allowed; jsdom cannot run it, so stand in for the lens here
// — children pass through because the composer textarea lives inside the lens
// (GlassOrb's own tests cover the fallback decision).
vi.mock('@samasante/liquid-glass', () => ({
  Glass: ({ children }: { children?: ReactNode }) => (
    <div data-testid="mock-glass">{children}</div>
  ),
}))

type ChatResponse = components['schemas']['ChatResponse']
type ResourceOut = components['schemas']['ResourceOut']

vi.mock('../api/client', () => ({
  sendChat: vi.fn(),
  fetchResources: vi.fn(),
  ApiUnavailableError: class ApiUnavailableError extends Error {
    constructor(message: string) {
      super(message)
      this.name = 'ApiUnavailableError'
    }
  },
  BadRequestError: class BadRequestError extends Error {
    constructor(message: string) {
      super(message)
      this.name = 'BadRequestError'
    }
  },
  NetworkError: class NetworkError extends Error {
    constructor(message: string) {
      super(message)
      this.name = 'NetworkError'
    }
  },
}))

const mockSendChat = vi.mocked(sendChat)
const mockFetchResources = vi.mocked(fetchResources)

const CRISIS_RESOURCES: ResourceOut[] = [
  { name: 'Find A Helpline (IASP global directory)', url: 'https://findahelpline.com' },
  { name: '988 Suicide & Crisis Lifeline (US)', url: 'https://988lifeline.org' },
  { name: 'If you are in immediate danger, contact your local emergency services', url: null },
]

const GENERATED_REPLY: ChatResponse = {
  reply: 'A short grounding exercise might help.',
  route: 'generated',
  module_ids: ['grounding_54321'],
  violations: [],
  resources: [],
}

const CRISIS_REPLY: ChatResponse = {
  reply: "I'm really sorry you're carrying this right now — please reach out to people who can help.",
  route: 'crisis_bypass',
  module_ids: [],
  violations: [],
  resources: CRISIS_RESOURCES,
}

const REVIEW_REPLY: ChatResponse = {
  reply: "There are some things I'm not able to do — I'm a wellness companion.",
  route: 'human_review',
  module_ids: [],
  violations: [],
  resources: [],
}

const FILTERED_REPLY: ChatResponse = {
  reply: 'I want to be careful with my words here.',
  route: 'filtered_fallback',
  module_ids: [],
  violations: [],
  resources: [],
}

function renderChatPage() {
  return render(
    <MemoryRouter>
      <EffectsProvider>
        <ToastProvider>
          <ChatPage />
        </ToastProvider>
      </EffectsProvider>
    </MemoryRouter>,
  )
}

function composer() {
  return screen.getByLabelText(/message/i)
}

async function send(user: ReturnType<typeof userEvent.setup>, text: string) {
  await user.type(composer(), text)
  await user.click(screen.getByRole('button', { name: 'Send' }))
}

beforeEach(() => {
  mockSendChat.mockReset()
  mockFetchResources.mockReset()
})

describe('ChatPage — empty state', () => {
  it('shows an honest prompt and the glass orb before the first message', () => {
    renderChatPage()
    expect(screen.getByText("What's on your mind?")).toBeInTheDocument()
    expect(screen.getByTestId('glass-orb')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('drops the empty-state orb once the conversation starts', async () => {
    const user = userEvent.setup()
    mockSendChat.mockResolvedValue(GENERATED_REPLY)
    renderChatPage()

    await send(user, 'hello')

    expect(screen.queryByTestId('glass-orb')).not.toBeInTheDocument()
  })
})

describe('ChatPage — happy path', () => {
  it('appends the user message and the assistant reply', async () => {
    const user = userEvent.setup()
    mockSendChat.mockResolvedValue(GENERATED_REPLY)
    renderChatPage()

    await send(user, 'I keep replaying an argument in my head')

    expect(
      screen.getByText('I keep replaying an argument in my head'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('A short grounding exercise might help.'),
    ).toBeInTheDocument()
    expect(mockSendChat).toHaveBeenCalledWith(
      'I keep replaying an argument in my head',
    )
    await waitFor(() =>
      expect(screen.queryByText('Getting a reply…')).not.toBeInTheDocument(),
    )
  })

  it('never renders internal violations from the response', async () => {
    const user = userEvent.setup()
    mockSendChat.mockResolvedValue({
      ...GENERATED_REPLY,
      violations: ['internal-lexer-flag:diagnos'],
    })
    renderChatPage()

    await send(user, 'hello')

    expect(screen.queryByText(/internal-lexer-flag/)).not.toBeInTheDocument()
  })

  it('clears the empty-state prompt once the conversation starts', async () => {
    const user = userEvent.setup()
    mockSendChat.mockResolvedValue(GENERATED_REPLY)
    renderChatPage()

    await send(user, 'hello')
    expect(screen.queryByText("What's on your mind?")).not.toBeInTheDocument()
  })
})

describe('ChatPage — pending state', () => {
  it('disables the composer and shows the honest pending status', async () => {
    const user = userEvent.setup()
    let resolve!: (value: ChatResponse) => void
    mockSendChat.mockImplementation(
      () => new Promise<ChatResponse>((r) => (resolve = r)),
    )
    renderChatPage()

    await user.type(composer(), 'hello')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(screen.getByText('Getting a reply…')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(composer()).toBeDisabled()

    resolve(GENERATED_REPLY)
    await waitFor(() =>
      expect(screen.queryByText('Getting a reply…')).not.toBeInTheDocument(),
    )
    expect(composer()).toBeEnabled()
  })
})

describe('ChatPage — crisis escalation (sticky)', () => {
  it('shows the banner, resources, and scripted reply for a crisis response', async () => {
    const user = userEvent.setup()
    mockSendChat.mockResolvedValue(CRISIS_REPLY)
    renderChatPage()

    await send(user, 'I want to kill myself')

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Immediate support matters right now.',
    )
    expect(
      screen.getByRole('link', { name: /Find A Helpline/ }),
    ).toHaveAttribute('href', 'https://findahelpline.com')
    expect(
      screen.getByRole('link', { name: /988 Suicide/ }),
    ).toHaveAttribute('href', 'https://988lifeline.org')
    expect(screen.getByText(CRISIS_REPLY.reply)).toBeInTheDocument()
    // The model path was never taken: no unavailable notice.
    expect(
      screen.queryByText(/assistant is unavailable/i),
    ).not.toBeInTheDocument()
  })

  it('keeps the banner and resources after later, non-crisis sends', async () => {
    const user = userEvent.setup()
    mockSendChat.mockResolvedValueOnce(CRISIS_REPLY).mockResolvedValue(GENERATED_REPLY)
    renderChatPage()

    await send(user, 'I want to kill myself')
    await send(user, 'thank you, that helps')

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /988 Suicide/ }),
    ).toBeInTheDocument()
  })

  it('renders the crisis reply with the plain assistant variant (not muted)', async () => {
    const user = userEvent.setup()
    mockSendChat.mockResolvedValue(CRISIS_REPLY)
    const { container } = renderChatPage()

    await send(user, 'I want to kill myself')

    const bubbles = container.querySelectorAll('[data-variant]')
    const last = bubbles[bubbles.length - 1]!
    expect(last.getAttribute('data-variant')).toBe('assistant')
  })
})

describe('ChatPage — route variants', () => {
  it('renders a human_review reply with the muted variant', async () => {
    const user = userEvent.setup()
    mockSendChat.mockResolvedValue(REVIEW_REPLY)
    const { container } = renderChatPage()

    await send(user, 'please diagnose my anxiety')

    const bubbles = container.querySelectorAll('[data-variant]')
    expect(bubbles[bubbles.length - 1]!.getAttribute('data-variant')).toBe('muted')
  })

  it('renders a filtered_fallback reply with the muted variant', async () => {
    const user = userEvent.setup()
    mockSendChat.mockResolvedValue(FILTERED_REPLY)
    const { container } = renderChatPage()

    await send(user, 'hello')

    const bubbles = container.querySelectorAll('[data-variant]')
    expect(bubbles[bubbles.length - 1]!.getAttribute('data-variant')).toBe(
      'muted',
    )
  })
})

describe('ChatPage — error paths', () => {
  it('shows the unavailable notice plus fetched resources on ApiUnavailableError', async () => {
    const user = userEvent.setup()
    mockSendChat.mockRejectedValue(
      new ApiUnavailableError(
        'The assistant is unavailable right now. You can still reach crisis support below.',
      ),
    )
    mockFetchResources.mockResolvedValue(CRISIS_RESOURCES)
    renderChatPage()

    await send(user, 'hello')

    expect(
      screen.getByText(
        'The assistant is unavailable right now. You can still reach crisis support below.',
      ),
    ).toBeInTheDocument()
    expect(mockFetchResources).toHaveBeenCalledTimes(1)
    expect(
      await screen.findByRole('link', { name: /Find A Helpline/ }),
    ).toBeInTheDocument()
  })

  it('stands on the notice alone when the resources fetch also fails', async () => {
    const user = userEvent.setup()
    mockSendChat.mockRejectedValue(
      new ApiUnavailableError('The assistant is unavailable right now.'),
    )
    mockFetchResources.mockRejectedValue(new NetworkError('offline'))
    renderChatPage()

    await send(user, 'hello')

    expect(
      screen.getByText(/assistant is unavailable right now/i),
    ).toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('shows the offline notice on NetworkError', async () => {
    const user = userEvent.setup()
    mockSendChat.mockRejectedValue(
      new NetworkError('You appear to be offline.'),
    )
    renderChatPage()

    await send(user, 'hello')

    expect(
      screen.getByText('You appear to be offline. Check your connection and try again.'),
    ).toBeInTheDocument()
    expect(mockFetchResources).not.toHaveBeenCalled()
  })

  it('shows the shorten-it notice on BadRequestError', async () => {
    const user = userEvent.setup()
    mockSendChat.mockRejectedValue(new BadRequestError('bad request'))
    renderChatPage()

    await send(user, 'hello')

    expect(
      screen.getByText(
        "Your message couldn't be sent. Please shorten it and try again.",
      ),
    ).toBeInTheDocument()
  })

  it('clears a previous error when the next send succeeds', async () => {
    const user = userEvent.setup()
    mockSendChat
      .mockRejectedValueOnce(new NetworkError('offline'))
      .mockResolvedValueOnce(GENERATED_REPLY)
    renderChatPage()

    await send(user, 'hello')
    expect(screen.getByText(/appear to be offline/i)).toBeInTheDocument()

    await send(user, 'trying again')
    expect(screen.queryByText(/appear to be offline/i)).not.toBeInTheDocument()
    expect(screen.getByText(GENERATED_REPLY.reply)).toBeInTheDocument()
  })

  it('keeps the user message in the transcript when a send fails', async () => {
    const user = userEvent.setup()
    mockSendChat.mockRejectedValue(new NetworkError('offline'))
    renderChatPage()

    await send(user, 'my message stays')

    expect(screen.getByText('my message stays')).toBeInTheDocument()
  })

  it('logs and shows generic copy for an unexpected error (no invented specifics)', async () => {
    const user = userEvent.setup()
    mockSendChat.mockRejectedValue(new Error('totally unexpected'))
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    renderChatPage()

    await send(user, 'hello')

    // The specific notices are fixed copy for KNOWN errors only; anything
    // else gets a generic honest line plus a developer-facing log.
    expect(
      screen.queryByText(/offline|unavailable|shorten/i),
    ).not.toBeInTheDocument()
    expect(screen.getByText('Something went wrong. Please try again.')).toBeInTheDocument()
    expect(spy).toHaveBeenCalledWith('chat send failed', expect.any(Error))
    spy.mockRestore()
  })
})

describe('ChatPage — connection toasts', () => {
  it('shows an offline toast when the window goes offline', async () => {
    renderChatPage()

    act(() => {
      window.dispatchEvent(new Event('offline'))
    })

    expect(await screen.findByRole('status')).toHaveTextContent(
      "You're offline — messages won't send until you're back.",
    )
  })

  it('shows a back-online toast when the window comes back online', async () => {
    renderChatPage()

    act(() => {
      window.dispatchEvent(new Event('online'))
    })

    expect(await screen.findByRole('status')).toHaveTextContent('Back online.')
  })
})

describe('ChatPage — input guards', () => {
  it('blocks empty and whitespace-only sends', async () => {
    const user = userEvent.setup()
    renderChatPage()

    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    await user.type(composer(), '   ')
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    await user.keyboard('{Enter}')
    expect(mockSendChat).not.toHaveBeenCalled()
  })

  it('sends on Enter and inserts a newline on Shift+Enter', async () => {
    const user = userEvent.setup()
    mockSendChat.mockResolvedValue(GENERATED_REPLY)
    renderChatPage()

    await user.type(composer(), 'first line{Shift>}{Enter}{/Shift}second line')
    expect(composer()).toHaveValue('first line\nsecond line')
    expect(mockSendChat).not.toHaveBeenCalled()

    await user.keyboard('{Enter}')
    expect(mockSendChat).toHaveBeenCalledWith('first line\nsecond line')
  })

  it('respects the 4000-character composer bound', () => {
    renderChatPage()
    expect(composer()).toHaveAttribute('maxLength', '4000')
  })
})

describe('ChatPage — transcript semantics', () => {
  it('renders assistant bubbles with the RE:FRAME aria-label', async () => {
    const user = userEvent.setup()
    mockSendChat.mockResolvedValue(GENERATED_REPLY)
    renderChatPage()

    await send(user, 'hello')

    const assistant = screen.getByLabelText('RE:FRAME')
    expect(within(assistant).getByText(GENERATED_REPLY.reply)).toBeInTheDocument()
  })
})
