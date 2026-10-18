/**
 * Composer (stage 6b): a length-bounded textarea with an accessible label,
 * Enter to send / Shift+Enter for a newline, send blocked for empty or
 * whitespace-only input, and an honest subdued pending state while a reply
 * is in flight — NO fake streaming animation (docs/webapp-design.md §5.3).
 */
import { useState, type KeyboardEvent } from 'react'

export const MESSAGE_MAX_LENGTH = 4000

export interface ComposerProps {
  onSend: (message: string) => void
  pending: boolean
}

export function Composer({ onSend, pending }: ComposerProps) {
  const [value, setValue] = useState('')
  const trimmed = value.trim()
  const canSend = trimmed.length > 0 && !pending

  function send() {
    if (!canSend) return
    onSend(trimmed)
    setValue('')
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      send()
    }
  }

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        send()
      }}
    >
      <label htmlFor="composer-input" className="sr-only">
        Message
      </label>
      <textarea
        id="composer-input"
        aria-label="Message"
        value={value}
        maxLength={MESSAGE_MAX_LENGTH}
        disabled={pending}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        rows={3}
        placeholder="Type a message…"
        className="rounded-[var(--radius-input)] border border-border bg-surface-sunk px-3 py-2 text-ink placeholder:text-ink-muted focus-visible:border-accent focus-visible:outline-none"
      />
      <div className="flex items-center justify-between gap-3">
        <span aria-live="polite" className="text-sm text-ink-muted">
          {pending ? 'Getting a reply…' : ''}
        </span>
        <button
          type="submit"
          disabled={!canSend}
          className="rounded-[var(--radius-pill)] bg-accent px-4 py-2 text-sm text-bg transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </form>
  )
}
