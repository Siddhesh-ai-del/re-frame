/**
 * DashboardStatusBar (stage 6d): the honest at-a-glance summary of the most
 * recent check-in across instruments. adapted from ObsidianUI status-bar
 * (MIT) — reshaped to RE:FRAME's design rules: NO streaks, NO guilt language,
 * NO counts-as-achievement framing (docs/webapp-design.md §3 row 5).
 *
 * The page computes the aggregate (it fetches every instrument's history);
 * this component only presents it. The loaded state is static content (no
 * live-region noise); only the loading and failure notes are announced.
 */

export interface DashboardLatest {
  readonly date: string
  readonly title: string
}

export interface DashboardStatusBarProps {
  /** The most recent check-in across instruments, or null if none loaded. */
  latest: DashboardLatest | null
  /** True while any history request is still in flight. */
  loading: boolean
  /** True when at least one history request failed. */
  failed: boolean
}

export function DashboardStatusBar({ latest, loading, failed }: DashboardStatusBarProps) {
  return (
    <section
      aria-label="Dashboard status"
      className="panel rounded-[var(--radius-card)] px-4 py-3"
    >
      {loading && (
        <p role="status" className="text-sm text-ink-muted">
          Loading your check-in history…
        </p>
      )}
      {failed && (
        <p role="status" className="text-sm text-ink-muted">
          Some of your check-in history couldn&apos;t be loaded right now.
        </p>
      )}
      {latest !== null ? (
        <p className="text-sm text-ink">
          Most recent check-in:{' '}
          <time dateTime={latest.date} className="tabular-nums">
            {latest.date}
          </time>{' '}
          — {latest.title}
        </p>
      ) : (
        // "No check-ins yet." is only honest when the histories actually
        // loaded — after a failure we simply don't know, so say nothing
        // rather than inventing an empty state (design §5.3).
        !loading && !failed && (
          <p className="text-sm text-ink-muted">No check-ins yet.</p>
        )
      )}
    </section>
  )
}
