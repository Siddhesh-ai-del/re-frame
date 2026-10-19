import { useEffect, useState } from 'react'
import { fetchResources } from '../../api/client'
import { CRISIS_BANNER_COPY } from '../chat/CrisisBanner'
import { ResourcesPanel } from '../chat/ResourcesPanel'
import type { components } from '../../api/schema.d'

/**
 * FlagNotice (stage 6d): the verbatim escalation layer above the result
 * (docs/webapp-design.md §5.2, D9). The API's `message` is presented EXACTLY
 * as returned — no re-wording, no paraphrase, no truncation. Semantics follow
 * the routing action: proceed → nothing; human_review → role="status" concern
 * panel; hard_bypass → role="alert" with crisis-banner styling plus
 * always-visible support resources (escalation is never toast-only).
 *
 * The banner styling here reuses CrisisBanner's copy but is NOT itself a
 * role="alert" element — the verbatim message is the single alert, so screen
 * readers announce exactly one assertive region containing the API's own
 * wording (a second nested alert would fragment the announcement).
 */

type CheckInOut = components['schemas']['CheckInOut']
type ResourceOut = components['schemas']['ResourceOut']

export interface FlagNoticeProps {
  result: CheckInOut
}

export function FlagNotice({ result }: FlagNoticeProps) {
  const [resources, setResources] = useState<ResourceOut[] | null>(null)
  const [resourcesFailed, setResourcesFailed] = useState(false)

  const isCrisis = result.action === 'hard_bypass'
  const isConcern = result.action === 'human_review'

  useEffect(() => {
    if (!isCrisis) return
    let cancelled = false
    const load = async () => {
      try {
        const loaded = await fetchResources()
        if (cancelled) return
        // A non-array result (e.g. an unexpected shape) reads as a failure —
        // never render a "resources" panel over data that isn't there.
        if (Array.isArray(loaded)) {
          setResources(loaded)
        } else {
          setResourcesFailed(true)
        }
      } catch {
        if (!cancelled) setResourcesFailed(true)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [isCrisis])

  if (!isCrisis && !isConcern) return null
  if (result.message === null) return null

  if (isConcern) {
    return (
      <div
        role="status"
        className="rounded-[var(--radius-card)] border border-border bg-warning-soft px-4 py-3 text-sm text-ink"
      >
        {result.message}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        data-testid="crisis-banner"
        className="rounded-[var(--radius-card)] border border-crisis bg-crisis-soft px-4 py-3 text-crisis"
      >
        {CRISIS_BANNER_COPY}
      </div>
      <div
        role="alert"
        className="rounded-[var(--radius-card)] border border-crisis bg-crisis-soft px-4 py-3 text-sm text-ink"
      >
        {result.message}
      </div>
      {resources !== null && <ResourcesPanel resources={resources} />}
      {resourcesFailed && (
        <p className="text-sm text-ink-muted">
          The support links couldn&apos;t load right now.
        </p>
      )}
    </div>
  )
}
