/**
 * Chat message bubble (stage 6b, adapted from opensourceui chat bubbles, MIT;
 * restyled for Golden Glass — spec §5).
 *
 * Two variants: `user` (terracotta CTA gradient + --cta-text, right) and
 * `assistant` (warm panel, left). The assistant variant goes `muted` on the
 * human_review and filtered_fallback routes so boundary copy reads visibly
 * softer. Internal fields (`violations`) are never rendered — the component
 * only accepts the text it should show.
 */

export type MessageRole = 'user' | 'assistant'

export interface MessageBubbleProps {
  role: MessageRole
  text: string
  /** The API route this message came from; only the assistant variant uses it. */
  route?: string
}

/** Routes whose assistant copy renders muted (softer, boundary tone). */
const MUTED_ROUTES = new Set(['human_review', 'filtered_fallback'])

export function MessageBubble({ role, text, route }: MessageBubbleProps) {
  if (role === 'user') {
    return (
      <li
        data-variant="user"
        className="bubble-user flex self-end rounded-[var(--radius-card)] rounded-br-[7px] shadow-[0_8px_22px_rgba(168,80,28,0.3)]"
        aria-label="You"
      >
        <div className="max-w-[85%] px-4 py-3">{text}</div>
      </li>
    )
  }

  const muted = route !== undefined && MUTED_ROUTES.has(route)
  return (
    <li
      data-variant={muted ? 'muted' : 'assistant'}
      className={[
        'flex self-start rounded-[var(--radius-card)] rounded-bl-[7px] border border-border bg-surface',
        muted ? 'text-ink-muted' : '',
      ].join(' ')}
      aria-label="RE:FRAME"
    >
      <div className="max-w-[85%] px-4 py-3">{text}</div>
    </li>
  )
}
