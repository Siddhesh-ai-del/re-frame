/**
 * ExercisesPage (stage 6c): the library screen. Verifies honest loading and
 * failure states (with a retry that actually refetches), category grouping
 * with readable headings, and that the FocusBreath widget and the
 * device-local JournalCard both render on the page.
 */
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EffectsProvider } from '../effects/EffectsContext'
import { fetchExercises } from '../api/client'
import { ExercisesPage } from './ExercisesPage'
import type { components } from '../api/schema.d'

type ExerciseOut = components['schemas']['ExerciseOut']

vi.mock('../api/client', () => ({
  fetchExercises: vi.fn(),
}))

const mockFetchExercises = vi.mocked(fetchExercises)

const LIBRARY: ExerciseOut[] = [
  {
    id: 'rumination-postponement',
    title: 'Thought postponement',
    summary: 'Set aside a short, fixed window for the looping thoughts.',
    category: 'rumination',
    tier: 'A',
    steps: ['Notice the loop.', 'Park it for later.'],
    sources: ['Stenzel et al. 2025'],
    contraindications: [],
    early_worsening_notice: true,
  },
  {
    id: 'self-compassion-break',
    title: 'Self-compassion break',
    summary: 'A short pause with kinder inner language.',
    category: 'self_compassion',
    tier: 'B',
    steps: ['Notice the moment.', 'Offer yourself a kind sentence.'],
    sources: ['Krieger et al. 2019'],
    contraindications: [],
    early_worsening_notice: true,
  },
  {
    id: 'concreteness-training',
    title: 'Concreteness training',
    summary: 'Describe a difficult event in plain, specific facts.',
    category: 'rumination',
    tier: 'A',
    steps: ['Pick a recent moment.', 'Describe only what happened.'],
    sources: ['Stenzel et al. 2025'],
    contraindications: [],
    early_worsening_notice: true,
  },
]

function renderPage() {
  return render(
    <EffectsProvider>
      <ExercisesPage />
    </EffectsProvider>,
  )
}

beforeEach(() => {
  mockFetchExercises.mockReset()
})

describe('ExercisesPage — loading and failure', () => {
  it('shows an honest loading state while the library is in flight', () => {
    mockFetchExercises.mockReturnValue(new Promise(() => {}))

    renderPage()

    expect(screen.getByText('Loading exercises…')).toBeInTheDocument()
  })

  it('shows the failure notice and a working retry on fetch failure', async () => {
    const user = userEvent.setup()
    mockFetchExercises.mockRejectedValueOnce(new Error('boom')).mockResolvedValueOnce(LIBRARY)

    renderPage()

    expect(
      await screen.findByText(
        "The exercise library couldn't be loaded right now. Please try again.",
      ),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /try again/i }))

    expect(await screen.findByText('Thought postponement')).toBeInTheDocument()
    expect(mockFetchExercises).toHaveBeenCalledTimes(2)
  })
})

describe('ExercisesPage — library grouping', () => {
  it('groups exercises under readable category headings', async () => {
    mockFetchExercises.mockResolvedValue(LIBRARY)

    renderPage()

    expect(await screen.findByRole('heading', { name: 'Rumination' })).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Self-Compassion' }),
    ).toBeInTheDocument()
    // Underscores are gone from the visible headings.
    expect(screen.queryByText(/self_compassion/)).not.toBeInTheDocument()

    const cards = screen.getAllByTestId('exercise-card')
    expect(cards).toHaveLength(3)
    const rumination = screen.getByRole('region', { name: 'Rumination' })
    expect(within(rumination).getAllByTestId('exercise-card')).toHaveLength(2)
  })

  it('renders steps and the honest evidence tier label on each card', async () => {
    mockFetchExercises.mockResolvedValue(LIBRARY)

    renderPage()

    await waitFor(() =>
      expect(screen.getAllByTestId('exercise-card')).toHaveLength(3),
    )
    // Two tier-A modules and one tier-B in the fixture.
    expect(screen.getAllByText('Evidence tier: A')).toHaveLength(2)
    expect(screen.getByText('Evidence tier: B')).toBeInTheDocument()
    expect(screen.getByText('Notice the loop.')).toBeInTheDocument()
  })
})

describe('ExercisesPage — companion widgets', () => {
  it('renders the focus-breath widget and the device-local journal', async () => {
    mockFetchExercises.mockResolvedValue(LIBRARY)

    renderPage()

    expect(
      await screen.findByRole('region', { name: 'Focus breath' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Journal' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Start' })).toBeInTheDocument()
  })
})
