/**
 * Chat screen (stage 6b): the conversation surface with honest states.
 *
 * State machine: empty → (send) → pending → reply appended | honest error
 * notice. A crisis_bypass reply flips the page into escalation: the sticky
 * assertive banner and the resources panel appear ONCE and persist for the
 * rest of the session (no close control — fail-closed). Generation
 * unavailability (503, no LLM key) shows the fixed unavailable notice plus a
 * best-effort fetch of GET /resources; if that fetch also fails, the notice
 * alone stands. Internal fields (violations) never reach the DOM.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  ApiUnavailableError,
  BadRequestError,
  NetworkError,
  fetchResources,
  sendChat,
  type ResourceOut,
} from '../api/client'
import { Composer } from '../components/chat/Composer'
import { CrisisBanner } from '../components/chat/CrisisBanner'
import { MessageBubble, type MessageRole } from '../components/chat/MessageBubble'
import { ResourcesPanel } from '../components/chat/ResourcesPanel'
import { GlassOrb } from '../components/onboarding/GlassOrb'
import { useToast } from '../components/toast/ToastProvider'

interface ChatMessage {
  id: number
  role: MessageRole
  text: string
  route?: string
}

const EMPTY_STATE_PROMPT = "What's on your mind?"
const OFFLINE_TOAST = "You're offline — messages won't send until you're back."
const ONLINE_TOAST = 'Back online.'
const NETWORK_ERROR_NOTICE =
  'You appear to be offline. Check your connection and try again.'
const BAD_REQUEST_NOTICE =
  "Your message couldn't be sent. Please shorten it and try again."

/** Map a client error onto its honest inline notice (fixed copy, no body text). */
function noticeFor(error: unknown): string | null {
  if (error instanceof ApiUnavailableError) {
    return 'The assistant is unavailable right now. You can still reach crisis support below.'
  }
  if (error instanceof NetworkError) return NETWORK_ERROR_NOTICE
  if (error instanceof BadRequestError) return BAD_REQUEST_NOTICE
  return null
}

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [pending, setPending] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [escalated, setEscalated] = useState(false)
  const [crisisResources, setCrisisResources] = useState<ResourceOut[]>([])
  const [fallbackResources, setFallbackResources] = useState<ResourceOut[]>([])
  const showtoast = useToast()

  // Connection toasts: only the offline/online transitions toast in 6b.
  useEffect(() => {
    const handleOffline = () => showtoast(OFFLINE_TOAST)
    const handleOnline = () => showtoast(ONLINE_TOAST)
    window.addEventListener('offline', handleOffline)
    window.addEventListener('online', handleOnline)
    return () => {
      window.removeEventListener('offline', handleOffline)
      window.removeEventListener('online', handleOnline)
    }
  }, [showtoast])

  const handleSend = useCallback(async (text: string) => {
    setPending(true)
    setNotice(null)
    setMessages((prev) => [
      ...prev,
      { id: prev.length, role: 'user', text },
    ])
    try {
      const response = await sendChat(text)
      setMessages((prev) => [
        ...prev,
        {
          id: prev.length,
          role: 'assistant',
          text: response.reply,
          route: response.route,
        },
      ])
      if (response.route === 'crisis_bypass') {
        // Sticky escalation: banner + resources persist for the session.
        setEscalated(true)
        setCrisisResources(response.resources)
      }
    } catch (error) {
      const mapped = noticeFor(error)
      if (mapped === null) {
        // Unknown failure: log it (developer signal) and show honest generic copy.
        console.error('chat send failed', error)
        setNotice('Something went wrong. Please try again.')
      } else {
        setNotice(mapped)
      }
      if (error instanceof ApiUnavailableError) {
        // Best-effort resources for the unavailable state; notice alone if this fails.
        try {
          setFallbackResources(await fetchResources())
        } catch {
          setFallbackResources([])
        }
      }
    } finally {
      setPending(false)
    }
  }, [])

  // Once escalated, resources come from the crisis response; the unavailable
  // state uses its own best-effort fetch.
  const shownResources = escalated ? crisisResources : fallbackResources

  return (
    <section
      aria-label="Chat"
      className="mx-auto flex w-full max-w-[720px] flex-col gap-4 px-6 py-8"
    >
      <h1 className="text-2xl font-medium text-ink">Chat</h1>
      {escalated && <CrisisBanner />}
      {messages.length === 0 ? (
        // Empty state (6c): the signature orb sits above the honest prompt.
        <div className="flex flex-col items-center gap-4 py-8">
          <GlassOrb size={120} />
          <p className="text-center text-ink-muted">{EMPTY_STATE_PROMPT}</p>
        </div>
      ) : (
        <ul
          aria-live="polite"
          aria-label="Conversation"
          className="flex flex-col gap-3"
        >
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              role={message.role}
              text={message.text}
              route={message.route}
            />
          ))}
        </ul>
      )}
      {notice !== null && (
        <p
          role="status"
          className="rounded-[var(--radius-card)] border border-border bg-surface-sunk px-4 py-3 text-ink"
        >
          {notice}
        </p>
      )}
      {shownResources.length > 0 && <ResourcesPanel resources={shownResources} />}
      <Composer onSend={handleSend} pending={pending} />
    </section>
  )
}
