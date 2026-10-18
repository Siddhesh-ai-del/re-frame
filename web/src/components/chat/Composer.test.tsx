/**
 * Composer: length-bounded textarea with an accessible label, Enter to send /
 * Shift+Enter for newline, send blocked for empty or whitespace-only input,
 * and an honest subdued pending state (no fake streaming animation).
 */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Composer } from './Composer'

describe('Composer', () => {
  it('renders a labelled textarea and a Send button', () => {
    render(<Composer onSend={vi.fn()} pending={false} />)
    expect(screen.getByLabelText(/message/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument()
  })

  it('bounds the message length at 4000 characters', () => {
    render(<Composer onSend={vi.fn()} pending={false} />)
    expect(screen.getByLabelText(/message/i)).toHaveAttribute(
      'maxLength',
      '4000',
    )
  })

  it('disables Send when the message is empty', () => {
    render(<Composer onSend={vi.fn()} pending={false} />)
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  })

  it('disables Send when the message is whitespace-only', async () => {
    const user = userEvent.setup()
    render(<Composer onSend={vi.fn()} pending={false} />)
    await user.type(screen.getByLabelText(/message/i), '   ')
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  })

  it('sends the trimmed message on click and clears the field', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<Composer onSend={onSend} pending={false} />)
    const textarea = screen.getByLabelText(/message/i)

    await user.type(textarea, '  I feel stuck  ')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(onSend).toHaveBeenCalledWith('I feel stuck')
    expect(textarea).toHaveValue('')
  })

  it('sends on Enter without a modifier key', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<Composer onSend={onSend} pending={false} />)
    const textarea = screen.getByLabelText(/message/i)

    await user.type(textarea, 'hello{Enter}')

    expect(onSend).toHaveBeenCalledWith('hello')
    expect(textarea).toHaveValue('')
  })

  it('inserts a newline on Shift+Enter instead of sending', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<Composer onSend={onSend} pending={false} />)
    const textarea = screen.getByLabelText(/message/i)

    await user.type(textarea, 'line one{Shift>}{Enter}{/Shift}line two')

    expect(onSend).not.toHaveBeenCalled()
    expect(textarea).toHaveValue('line one\nline two')
  })

  it('does not send whitespace-only input on Enter', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<Composer onSend={onSend} pending={false} />)

    await user.type(screen.getByLabelText(/message/i), '   {Enter}')

    expect(onSend).not.toHaveBeenCalled()
  })

  it('disables Send and shows an honest subdued status while pending', () => {
    render(<Composer onSend={vi.fn()} pending={true} />)
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(screen.getByText('Getting a reply…')).toBeInTheDocument()
    expect(screen.getByText('Getting a reply…')).toHaveAttribute(
      'aria-live',
      'polite',
    )
  })

  it('re-enables Send after pending clears, keeping the draft intact', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    const { rerender } = render(<Composer onSend={onSend} pending={false} />)
    const textarea = screen.getByLabelText(/message/i)
    await user.type(textarea, 'a draft kept while waiting')

    rerender(<Composer onSend={onSend} pending={true} />)
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()

    rerender(<Composer onSend={onSend} pending={false} />)
    expect(screen.getByRole('button', { name: 'Send' })).toBeEnabled()
    expect(textarea).toHaveValue('a draft kept while waiting')
  })
})
