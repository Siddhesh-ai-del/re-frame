/**
 * ResourcesPanel: real crisis-resource links (target=_blank, rel protected),
 * and non-linkable guidance rendered as plain text lines.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ResourcesPanel } from './ResourcesPanel'
import type { components } from '../../api/schema.d'

type ResourceOut = components['schemas']['ResourceOut']

const RESOURCES: ResourceOut[] = [
  { name: 'Find A Helpline (IASP global directory)', url: 'https://findahelpline.com' },
  { name: '988 Suicide & Crisis Lifeline (US)', url: 'https://988lifeline.org' },
  { name: 'If you are in immediate danger, contact your local emergency services', url: null },
]

describe('ResourcesPanel', () => {
  it('renders each resource name', () => {
    render(<ResourcesPanel resources={RESOURCES} />)
    for (const resource of RESOURCES) {
      expect(screen.getByText(resource.name)).toBeInTheDocument()
    }
  })

  it('renders linkable resources as external links with safe rel attributes', () => {
    render(<ResourcesPanel resources={RESOURCES} />)
    const helpline = screen.getByRole('link', {
      name: /Find A Helpline/,
    })
    expect(helpline).toHaveAttribute('href', 'https://findahelpline.com')
    expect(helpline).toHaveAttribute('target', '_blank')
    expect(helpline).toHaveAttribute('rel', 'noopener noreferrer')

    const lifeline = screen.getByRole('link', { name: /988 Suicide/ })
    expect(lifeline).toHaveAttribute('href', 'https://988lifeline.org')
  })

  it('renders null-url guidance as a plain text line, not a link', () => {
    const { container } = render(<ResourcesPanel resources={RESOURCES} />)
    const guidance = screen.getByText(/contact your local emergency services/)
    expect(guidance.closest('a')).toBeNull()
    expect(container.querySelectorAll('a')).toHaveLength(2)
  })

  it('renders nothing for an empty resource list', () => {
    const { container } = render(<ResourcesPanel resources={[]} />)
    expect(container.querySelectorAll('li')).toHaveLength(0)
    expect(container.querySelectorAll('a')).toHaveLength(0)
  })
})
