/**
 * CrisisBanner: the persistent, fail-closed escalation banner (stage 6b,
 * restyled in the Golden Glass direction — spec §5 "now warm amber-warn
 * styling, same copy + link").
 *
 * Once a crisis_bypass response has been seen, this renders for the rest of
 * the session with role="alert" + aria-live="assertive". It has NO close
 * control by design — escalation survives the UI layer (docs/webapp-design.md
 * §5.2), and it is never dismissible. Copy is byte-identical (safety copy).
 */

export const CRISIS_BANNER_COPY =
  'Immediate support matters right now. The resources below are free and available now.'

export function CrisisBanner() {
  return (
    <div
      data-testid="crisis-banner"
      role="alert"
      aria-live="assertive"
      className="sticky top-0 z-40 rounded-[var(--radius-card)] border border-warning bg-warning-soft px-4 py-3 font-medium text-warning"
    >
      {CRISIS_BANNER_COPY}
    </div>
  )
}
