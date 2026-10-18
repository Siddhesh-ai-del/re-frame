import type { ReactNode } from 'react'

/** Placeholder page shell; real screens land in stages 6b–6d. */
export function PagePlaceholder({
  title,
  children,
}: {
  title: string
  children?: ReactNode
}) {
  return (
    <section className="mx-auto w-full max-w-page px-6 py-12">
      <h1 className="text-3xl text-ink">{title}</h1>
      {children}
    </section>
  )
}
