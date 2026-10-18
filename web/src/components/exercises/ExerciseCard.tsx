/**
 * ExerciseCard (stage 6c): one library module rendered honestly.
 *
 * - The evidence tier is shown as a LABEL ONLY — "Evidence tier: A" — with
 *   no risk coloring of any kind (NICE NG225, design §5.4).
 * - Sources that are URLs render as plain links with rel="noopener
 *   noreferrer"; narrative citations render as plain text.
 * - Contraindications are surfaced verbatim when present ("Keep in mind").
 */
import type { components } from '../../api/schema.d'

export type ExerciseOut = components['schemas']['ExerciseOut']

function isUrl(value: string): boolean {
  return /^https?:\/\//.test(value)
}

export function ExerciseCard({ exercise }: { exercise: ExerciseOut }) {
  return (
    <article
      data-testid="exercise-card"
      className="flex flex-col gap-2 rounded-[var(--radius-card)] border border-border bg-surface p-4"
    >
      <h3 className="text-lg font-medium text-ink">{exercise.title}</h3>
      <p className="text-ink-muted">{exercise.summary}</p>
      {/* Honest label only — the tier is a grading, not a risk signal. */}
      <p className="text-sm text-ink-muted">Evidence tier: {exercise.tier}</p>
      <h4 className="text-sm font-medium text-ink">Steps</h4>
      <ol aria-label="Steps" className="list-decimal pl-5 text-ink">
        {exercise.steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      {exercise.contraindications.length > 0 && (
        <>
          <h4 className="text-sm font-medium text-ink">Keep in mind</h4>
          <ul className="list-disc pl-5 text-ink">
            {exercise.contraindications.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      )}
      <h4 className="text-sm font-medium text-ink">Sources</h4>
      <ul className="flex flex-col text-sm text-ink-muted">
        {exercise.sources.map((source) => (
          <li key={source}>
            {isUrl(source) ? (
              <a
                href={source}
                rel="noopener noreferrer"
                className="text-accent underline-offset-2 hover:underline"
              >
                {source}
              </a>
            ) : (
              source
            )}
          </li>
        ))}
      </ul>
    </article>
  )
}
