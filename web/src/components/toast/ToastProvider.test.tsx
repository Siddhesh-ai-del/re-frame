/**
 * Toast primitive: single toast slot, auto-dismiss after 4s (fake timers),
 * role="status" for non-critical confirmations only (escalation never toasts).
 * Uses fireEvent rather than userEvent so fake timers never stall the driver.
 */
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider, useToast } from './ToastProvider'

function ToastHarness() {
  const show = useToast()
  return (
    <button type="button" onClick={() => show('Check-in saved')}>
      Save
    </button>
  )
}

function TwoToastHarness() {
  const show = useToast()
  return (
    <>
      <button type="button" onClick={() => show('First')}>
        One
      </button>
      <button type="button" onClick={() => show('Second')}>
        Two
      </button>
    </>
  )
}

function renderToasts() {
  return render(
    <ToastProvider>
      <ToastHarness />
    </ToastProvider>,
  )
}

describe('ToastProvider', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('throws a helpful error when useToast is used outside the provider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<ToastHarness />)).toThrow(
      'useToast must be used within a ToastProvider',
    )
    spy.mockRestore()
  })

  it('renders the shown toast with role="status"', () => {
    renderToasts()

    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(screen.getByRole('status')).toHaveTextContent('Check-in saved')
  })

  it('auto-dismisses the toast after 4000ms', () => {
    renderToasts()

    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(screen.getByRole('status')).toBeInTheDocument()

    act(() => vi.advanceTimersByTime(3999))
    expect(screen.getByRole('status')).toBeInTheDocument()

    act(() => vi.advanceTimersByTime(1))
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('keeps a single toast slot — a new toast replaces the previous one', () => {
    render(
      <ToastProvider>
        <TwoToastHarness />
      </ToastProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'One' }))
    fireEvent.click(screen.getByRole('button', { name: 'Two' }))

    expect(screen.getAllByRole('status')).toHaveLength(1)
    expect(screen.getByRole('status')).toHaveTextContent('Second')
  })

  it('restarts the dismissal timer when a new toast replaces the current one', () => {
    render(
      <ToastProvider>
        <TwoToastHarness />
      </ToastProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'One' }))
    act(() => vi.advanceTimersByTime(3000))
    fireEvent.click(screen.getByRole('button', { name: 'Two' }))
    act(() => vi.advanceTimersByTime(3000))

    // 6000ms after the first toast but only 3000ms after the second: still up.
    expect(screen.getByRole('status')).toHaveTextContent('Second')

    act(() => vi.advanceTimersByTime(1000))
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('clears the pending dismissal timer when unmounted', () => {
    const view = renderToasts()

    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    view.unmount()

    // No timer should fire post-unmount (would leak or throw).
    expect(() => vi.advanceTimersByTime(4000)).not.toThrow()
  })
})
