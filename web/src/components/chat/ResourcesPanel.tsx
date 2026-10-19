/**
 * ResourcesPanel: real crisis resources as a link list (stage 6b).
 *
 * Linkable resources render as external links (target=_blank with
 * rel="noopener noreferrer"); guidance without a URL (e.g. "contact your
 * local emergency services") renders as a plain text line. Used both for
 * crisis responses (resources from the response) and for the honest 503
 * state (resources fetched from GET /resources).
 */
import type { components } from '../../api/schema.d'

type ResourceOut = components['schemas']['ResourceOut']

export interface ResourcesPanelProps {
  resources: ResourceOut[]
}

export function ResourcesPanel({ resources }: ResourcesPanelProps) {
  if (resources.length === 0) return null
  return (
    <section
      aria-label="Crisis support resources"
      className="panel rounded-[var(--radius-card)] p-4"
    >
      <h2 className="text-xs font-extrabold uppercase tracking-[0.14em] text-accent-ink">
        Support available now
      </h2>
      <ul className="mt-2 flex flex-col gap-1 text-sm">
        {resources.map((resource) => (
          <li key={resource.name} className="text-ink">
            {resource.url === null ? (
              <span>{resource.name}</span>
            ) : (
              <a
                href={resource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent underline underline-offset-2"
              >
                {resource.name}
              </a>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
