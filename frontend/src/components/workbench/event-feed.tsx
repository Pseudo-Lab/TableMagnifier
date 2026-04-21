import type { ReactNode } from 'react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'

type EventRecord = Record<string, unknown>

function asNumber(value: unknown): number | null {
  return typeof value === 'number' ? value : null
}

type EventFeedProps = {
  title: string
  description?: string
  events: EventRecord[]
  emptyText: string
  renderAction: (event: EventRecord) => string
  renderDetail: (event: EventRecord) => string
}

export function EventFeed({ title, description, events, emptyText, renderAction, renderDetail }: EventFeedProps) {
  return (
    <Card className="border-border/70">
      <CardHeader className="pb-4">
        <CardTitle className="text-base">{title}</CardTitle>
        {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[420px] pr-4">
          <div className="space-y-3">
            {events.length === 0 ? <p className="text-sm text-muted-foreground">{emptyText}</p> : null}
            {events.map((event, index) => {
              const stepIndex = asNumber(event.step_index)
              return (
                <article key={`${title}-${stepIndex ?? index}`} className="rounded-lg border border-border/70 bg-muted/30 p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <span className="rounded-full bg-secondary px-2 py-0.5 text-xs font-semibold text-secondary-foreground">
                      #{stepIndex ?? index + 1}
                    </span>
                    <strong className="text-sm font-semibold">{renderAction(event)}</strong>
                  </div>
                  <p className="text-sm leading-6 text-muted-foreground">{renderDetail(event)}</p>
                </article>
              )
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}

export function InfoGrid({ items }: { items: Array<{ label: string; value: ReactNode }> }) {
  return (
    <div className="grid grid-cols-2 gap-3">
      {items.map((item) => (
        <div key={item.label} className="rounded-lg border border-border/70 bg-muted/30 p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">{item.label}</p>
          <div className="text-sm font-medium leading-6 text-foreground">{item.value}</div>
        </div>
      ))}
    </div>
  )
}
