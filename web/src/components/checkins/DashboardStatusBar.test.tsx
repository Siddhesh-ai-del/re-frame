/**
 * DashboardStatusBar (stage 6d): the honest at-a-glance summary of the most
 * recent check-in across instruments. adapted from ObsidianUI status-bar
 * (MIT) — reshaped to the design rules: NO streaks, NO guilt language, NO
 * counts-as-achievement framing (docs/webapp-design.md §3 row 5).
 *
 * The page computes the aggregate (it fetches every instrument's history);
 * this component only presents it, including the honest loading/failure
 * states that must never pretend to data that didn't load.
 */
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DashboardStatusBar } from './DashboardStatusBar'

const LATEST = {
  date: '2026-10-18',
  title: 'Patient Health Questionnaire-9 (PHQ-9)',
}

function renderStatus(props: Partial<React.ComponentProps<typeof DashboardStatusBar>> = {}) {
  return render(
    <DashboardStatusBar latest={null} loading={false} failed={false} {...props} />,
  )
}

describe('DashboardStatusBar', () => {
  it('shows the most recent check-in as its date plus the instrument title', () => {
    renderStatus({ latest: LATEST })

    const region = screen.getByRole('region', { name: 'Dashboard status' })
    expect(region).toHaveTextContent('2026-10-18')
    expect(region).toHaveTextContent('Patient Health Questionnaire-9 (PHQ-9)')
  })

  it('renders the date as a machine-readable time element', () => {
    renderStatus({ latest: LATEST })
    expect(screen.getByRole('time')).toHaveAttribute('datetime', '2026-10-18')
  })

  it('says so plainly when there are no check-ins yet', () => {
    renderStatus()
    expect(screen.getByRole('region', { name: 'Dashboard status' })).toHaveTextContent(
      'No check-ins yet.',
    )
  })

  it('announces an honest loading state', () => {
    renderStatus({ loading: true })
    expect(screen.getByRole('status')).toHaveTextContent(
      'Loading your check-in history…',
    )
  })

  it('shows an honest failure note while staying usable (no fake empty state)', () => {
    renderStatus({ failed: true })

    const region = screen.getByRole('region', { name: 'Dashboard status' })
    expect(region).toHaveTextContent("couldn't be loaded")
    expect(region).not.toHaveTextContent('No check-ins yet.')
  })

  it('keeps showing the loaded latest alongside a partial-failure note', () => {
    renderStatus({ latest: LATEST, failed: true })

    const region = screen.getByRole('region', { name: 'Dashboard status' })
    expect(region).toHaveTextContent('2026-10-18')
    expect(region).toHaveTextContent("couldn't be loaded")
  })

  it('never uses streaks, guilt, or achievement-count language', () => {
    const { container } = renderStatus({ latest: LATEST })
    renderStatus({ failed: true })
    const text = container.textContent ?? ''
    expect(text).not.toMatch(/streak|days in a row|keep it up|you missed|don't break/i)
  })

  it('does not announce the loaded state as a live region (no noise)', () => {
    // The ready state is static content; only the loading/failure notes talk.
    renderStatus({ latest: LATEST })
    const region = screen.getByRole('region', { name: 'Dashboard status' })
    expect(within(region).queryByRole('status')).not.toBeInTheDocument()
  })
})
