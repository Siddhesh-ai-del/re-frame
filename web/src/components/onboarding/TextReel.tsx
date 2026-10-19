/**
 * TextReel (stage 6c): a short flip-headline for onboarding and empty states.
 * adapted from ObsidianUI (MIT) flip-text — condensed to the calm-minimal
 * direction: a plain word swap on a short interval, no per-letter churn.
 *
 * Honesty/motion contract (design §3 row 9): the reel is short and
 * interruptive only — it cycles a few words and PERMANENTLY settles on the
 * final headline (the timer clears itself; no infinite loop). Under reduced
 * effects the final text renders STATIC on the first paint: no intermediate
 * words, no timers at all.
 */
import { useEffect, useState } from 'react'
import { useReducedEffects } from '../../effects/EffectsContext'

export interface TextReelProps {
  /** 1–3 short words cycled before the headline settles. */
  words: readonly string[]
  /** The calm headline the reel settles on (also the reduced-motion text). */
  finalText: string
  /** Milliseconds each intermediate word is shown. */
  intervalMs?: number
}

export function TextReel({ words, finalText, intervalMs = 900 }: TextReelProps) {
  const { reducedEffects } = useReducedEffects()
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (reducedEffects) return
    if (index >= words.length) return
    const timer = setTimeout(() => setIndex((i) => i + 1), intervalMs)
    return () => clearTimeout(timer)
  }, [index, words.length, intervalMs, reducedEffects])

  const settled = reducedEffects || index >= words.length
  const text = settled ? finalText : (words[index] ?? finalText)

  return (
    <p
      data-testid="text-reel"
      {...(settled ? { 'data-static': 'true' } : {})}
      className="font-display text-center text-3xl font-medium italic text-accent-ink"
    >
      {text}
    </p>
  )
}
