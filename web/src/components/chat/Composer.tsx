/**
 * Composer (stage 6b/6f): a length-bounded textarea with an accessible label,
 * Enter to send / Shift+Enter for a newline, send blocked for empty or
 * whitespace-only input, and an honest subdued pending state while a reply
 * is in flight — NO fake streaming animation (docs/webapp-design.md §5.3).
 *
 * Stage 6f: the input row sits inside the shared liquid-glass pill (usage
 * site 3 of 3 — spec §4). The form, label, button, and keyboard behavior are
 * untouched; only the surrounding material changed (and the lens is swapped
 * for a static panel under reduced effects by GlassSurface itself).
 */
import { useState, type KeyboardEvent } from 'react'
import { GlassSurface } from '../glass/GlassSurface'

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
      <GlassSurface variant="composer" className="w-full" testId="composer-glass">
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
          className="min-h-[76px] flex-1 resize-none border-0 bg-transparent px-1 py-1 text-ink placeholder:text-ink-muted focus-visible:outline-2 focus-visible:outline-[var(--ring)]"
        />
        <button
          type="submit"
          disabled={!canSend}
          className="btn-cta flex-none rounded-pill px-5 py-2.5 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-50"
        >
          Send
        </button>
      </GlassSurface>
      <div className="flex justify-end">
        <span aria-live="polite" className="text-sm text-ink-muted">
          {pending ? 'Getting a reply…' : ''}
        </span>
      </div>
    </form>
  )
}
