/**
 * ExercisesPage (stage 6c): the exercise library screen.
 *
 * Loads the library from GET /content/exercises via the typed client and
 * groups it under readable category headings, each module as an
 * ExerciseCard. Honest states per design §5.3: an in-flight load says
 * "Loading exercises…"; a failed load says so plainly and offers a retry
 * that actually refetches. The FocusBreath break and the device-local
 * JournalCard render alongside the library.
 */
import { useCallback, useEffect, useState } from 'react'
import { fetchExercises, type ExerciseOut } from '../api/client'
import { ExerciseCard } from '../components/exercises/ExerciseCard'
import { FocusBreath } from '../components/exercises/FocusBreath'
import { JournalCard } from '../components/exercises/JournalCard'

const LOADING_TEXT = 'Loading exercises…'
const FAILURE_TEXT =
  "The exercise library couldn't be loaded right now. Please try again."

/** `self_compassion` → `Self-Compassion` (each segment capitalized, hyphenated). */
function readableCategory(category: string): string {
  // Uppercase ONLY each segment's first letter. Lowercasing the remainder
  // would re-case words like "passion" → "Passion" and break the
  // accessible-name contract ("Self-Compassion") that the tests rely on.
  return category
    .split('_')
    .map((seg) => seg.charAt(0).toUpperCase() + seg.slice(1))
    .join('-')
}

interface Group {
  category: string
  modules: ExerciseOut[]
}

function groupByCategory(exercises: ExerciseOut[]): Group[] {
  const groups: Group[] = []
  for (const exercise of exercises) {
    const existing = groups.find((group) => group.category === exercise.category)
    if (existing) {
      existing.modules.push(exercise)
    } else {
      groups.push({ category: exercise.category, modules: [exercise] })
    }
  }
  return groups
}

export function ExercisesPage() {
  const [exercises, setExercises] = useState<ExerciseOut[] | null>(null)
  const [failed, setFailed] = useState(false)
  // Bumped by the retry button to refetch; also lets tests re-run cleanly.
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    fetchExercises()
      .then((list) => {
        if (!cancelled) setExercises(list)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [attempt])

  const retry = useCallback(() => {
    // Clear the stale result/failure immediately (an event handler, so a
    // synchronous setState is fine here — not in the effect above).
    setExercises(null)
    setFailed(false)
    setAttempt((previous) => previous + 1)
  }, [])

  return (
    <section
      aria-label="Exercises"
      className="mx-auto flex w-full max-w-page flex-col gap-8 px-6 py-8"
    >
      <h1 className="font-display text-3xl font-bold tracking-[-0.01em] text-ink">
        Exercises
      </h1>
      {failed ? (
        <div className="flex flex-col items-start gap-3">
          <p role="status" className="text-ink">
            {FAILURE_TEXT}
          </p>
          <button
            type="button"
            onClick={retry}
            className="btn-cta rounded-pill px-4 py-2 text-sm font-semibold transition-colors duration-150"
          >
            Try again
          </button>
        </div>
      ) : exercises === null ? (
        <p role="status" className="text-ink-muted">
          {LOADING_TEXT}
        </p>
      ) : (
        groupByCategory(exercises).map((group) => (
          <div
            key={group.category}
            role="region"
            aria-label={readableCategory(group.category)}
            className="flex flex-col gap-3"
          >
            <h2 className="flex items-center gap-2.5 font-display text-xl font-bold tracking-[-0.01em] text-ink">
              <span
                aria-hidden="true"
                className="h-2.5 w-2.5 flex-none rounded-full bg-accent shadow-[0_0_0_3px_rgba(255,255,255,0.7)]"
              />
              {readableCategory(group.category)}
            </h2>
            <div className="grid gap-3 md:grid-cols-2">
              {group.modules.map((module) => (
                <ExerciseCard key={module.id} exercise={module} />
              ))}
            </div>
          </div>
        ))
      )}
      <FocusBreath />
      <JournalCard />
    </section>
  )
}
