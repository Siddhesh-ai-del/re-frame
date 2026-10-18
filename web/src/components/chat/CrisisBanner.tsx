/**
 * CrisisBanner: the persistent, fail-closed escalation banner (stage 6b).
 *
 * Once a crisis_bypass response has been seen, this renders for the rest of
 * the session with role="alert" + aria-live="assertive". It has NO close
 * control by design — escalation survives the UI layer (docs/webapp-design.md
 * §5.2), and it is never dismissible.
 */

export const CRISIS_BANNER_COPY =
  'Immediate support matters right now. The resources below are free and available now.'

export function CrisisBanner() {
  return (
    <div
      data-testid="crisis-banner"
      role="alert"
      aria-live="assertive"
      className="sticky top-0 z-40 rounded-[var(--radius-card)] border border-crisis bg-crisis-soft px-4 py-3 text-crisis"
    >
      {CRISIS_BANNER_COPY}
    </div>
  )
}
