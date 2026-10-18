import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

/**
 * Toast primitive (stage 6b).
 *
 * A SINGLE toast slot with a 4000ms auto-dismiss, rendered with
 * role="status" (polite — toasts are for non-critical confirmations only;
 * crisis escalation is never toast-only and never lands here). A new toast
 * replaces the current one and restarts the dismissal timer. The timer is
 * cleared on unmount so no state update fires after teardown.
 */

export type ShowToast = (text: string) => void

const DISMISS_MS = 4000

const ToastContext = createContext<ShowToast | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const show = useCallback<ShowToast>(
    (text) => {
      clearTimer()
      setToast(text)
      timerRef.current = setTimeout(() => {
        setToast(null)
        timerRef.current = null
      }, DISMISS_MS)
    },
    [clearTimer],
  )

  useEffect(() => clearTimer, [clearTimer])

  const value = useMemo(() => show, [show])

  return (
    <ToastContext.Provider value={value}>
      {children}
      {toast !== null && (
        <div
          role="status"
          className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-[var(--radius-card)] border border-border bg-surface px-4 py-3 text-sm text-ink shadow-[var(--shadow-soft)]"
        >
          {toast}
        </div>
      )}
    </ToastContext.Provider>
  )
}

export function useToast(): ShowToast {
  const show = useContext(ToastContext)
  if (show === null) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return show
}
