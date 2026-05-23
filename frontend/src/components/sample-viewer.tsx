import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, BookOpenText, CheckCircle2, FileText, Layers3, Send, Sparkles } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription } from '@/components/ui/card'
import type { Info, Observation } from '@/api'
import {
  normalizeSampleViewModel,
  type NormalizedEvidenceSection,
  type NormalizedSampleViewModel,
  type NormalizedTable,
  type NormalizedTextBlock,
  type NormalizedValidationIssue,
  type RenderMode,
} from '@/lib/sample-viewer-model'

type SampleViewerProps = {
  observation: Observation | null
  info: Info | null
  answer: string
  isLoading: boolean
  errorText: string
  renderMode?: RenderMode
  onAnswerChange: (answer: string) => void
  onSubmit: (answer: string) => void
}

function PageHeader({ model }: { model: NormalizedSampleViewModel }) {
  return (
    <header className="vtqa-header">
      <div className="vtqa-title-block">
        <div className="vtqa-app-mark" aria-hidden="true">
          <BookOpenText />
        </div>
        <div>
        <p className="vtqa-kicker">Visual TableQA</p>
        <h1>{model.header.title}</h1>
        {model.header.subtitle ? <p className="vtqa-subtitle">{model.header.subtitle}</p> : null}
        </div>
      </div>
      <div className="vtqa-status" aria-label="샘플 메타데이터">
        {model.header.badges?.map((badge) => (
          <Badge key={`${badge.label}-${badge.value ?? ''}`} variant={badge.tone === 'accent' ? 'default' : 'secondary'} className="vtqa-badge">
            {badge.value ? `${badge.label}: ${badge.value}` : badge.label}
          </Badge>
        ))}
      </div>
    </header>
  )
}

function PageNavigation({
  model,
  activePageKey,
  onSelect,
}: {
  model: NormalizedSampleViewModel
  activePageKey: string
  onSelect: (pageKey: string) => void
}) {
  if (model.pages.length === 0) {
    return null
  }

  return (
    <nav className="vtqa-page-nav" aria-label="문서 페이지">
      <div className="vtqa-page-nav-heading">
        <Layers3 aria-hidden="true" />
        <span>문서 탐색</span>
      </div>
      <div className="vtqa-page-tabs">
        {model.pages.map((page, index) => (
          <button key={`${page.key}-${index}`} type="button" className="vtqa-page-tab" data-active={page.key === activePageKey} onClick={() => onSelect(page.key)}>
            <span className="vtqa-page-tab-index">{String(index + 1).padStart(2, '0')}</span>
            <span>
              <strong>{page.label}</strong>
              {page.eyebrow ? <small>{page.eyebrow}</small> : null}
            </span>
          </button>
        ))}
      </div>
    </nav>
  )
}

function QuestionCard({ model }: { model: NormalizedSampleViewModel }) {
  return (
    <section className="vtqa-inspector-section vtqa-question" data-testid="question-card">
      <div className="vtqa-inspector-heading">
        <FileText aria-hidden="true" />
        <h2>{model.question.title}</h2>
      </div>
        <p>{model.question.text || '세션이 준비되면 질문이 표시됩니다.'}</p>
    </section>
  )
}

function SubmissionFormatCard({ model }: { model: NormalizedSampleViewModel }) {
  return (
    <section className="vtqa-inspector-section vtqa-format">
      <div className="vtqa-inspector-heading">
        <CheckCircle2 aria-hidden="true" />
        <h2>{model.submission.title}</h2>
      </div>
        {model.submission.description ? <CardDescription>{model.submission.description}</CardDescription> : null}
        <div className="vtqa-chip-row">
          {model.submission.formats.map((format) => (
            <span key={format.id} className="vtqa-chip">
              {format.label}
            </span>
          ))}
        </div>
    </section>
  )
}

function ValidationErrorState({ issues }: { issues: NormalizedValidationIssue[] }) {
  if (issues.length === 0) {
    return null
  }

  const highestSeverity = issues.some((issue) => issue.severity === 'error') ? 'error' : 'warning'
  return (
    <section className={`vtqa-validation is-${highestSeverity}`} role="status" aria-live="polite" data-testid="sample-validation-state">
      <AlertTriangle aria-hidden="true" />
      <div>
        <h2>{highestSeverity === 'error' ? '샘플 검증 오류' : '샘플 검증 경고'}</h2>
        <ul>
          {issues.map((issue) => (
            <li key={`${issue.code}-${issue.title}`}>
              <strong>{issue.title}</strong>
              <span>{issue.message}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

function EvidenceTable({ table, sectionTitle }: { table: NormalizedTable; sectionTitle: string }) {
  const caption = table.caption && table.caption !== sectionTitle ? table.caption : sectionTitle

  return (
    <div className="vtqa-table-wrap">
      <table aria-label={caption}>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {table.columns.map((column) => (
              <th key={column.id} scope="col" className={column.align ? `align-${column.align}` : undefined}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row) => (
            <tr key={row.id}>
              {row.cells.map((cell, index) => {
                const classNames = [cell.isUnknown ? 'is-unknown' : '', cell.align ? `align-${cell.align}` : ''].filter(Boolean).join(' ') || undefined
                const key = `${row.id}-${cell.columnId}-${index}`
                if (cell.asHeader) {
                  return (
                    <th key={key} scope="row" colSpan={cell.colSpan} rowSpan={cell.rowSpan} className={classNames}>
                      {cell.displayValue}
                    </th>
                  )
                }
                return (
                  <td key={key} colSpan={cell.colSpan} rowSpan={cell.rowSpan} className={classNames}>
                    {cell.displayValue}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function DocumentEvidenceBlock({ block }: { block: NormalizedTextBlock }) {
  if (block.type === 'list') {
    return (
      <ul className="vtqa-doc-block">
        {block.items?.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    )
  }
  if (block.type === 'keyValue') {
    return (
      <dl className="vtqa-doc-block vtqa-key-values">
        {block.pairs?.map((pair) => (
          <div key={pair.label}>
            <dt>{pair.label}</dt>
            <dd>{pair.value}</dd>
          </div>
        ))}
      </dl>
    )
  }
  return (
    <div className={`vtqa-doc-block is-${block.type}`}>
      {block.text?.split('\n').map((line) => (
        <p key={line}>{line}</p>
      ))}
    </div>
  )
}

function EvidenceSection({ section }: { section: NormalizedEvidenceSection }) {
  if (section.kind === 'validation') {
    return <ValidationErrorState issues={section.issues} />
  }

  const tables = 'tables' in section ? section.tables ?? [] : []
  const blocks = 'blocks' in section ? section.blocks ?? [] : []

  return (
    <section className="vtqa-evidence-block" data-evidence-kind={section.kind}>
      <div className="vtqa-section-heading">
        <h2>{section.title}</h2>
        {section.description ? <p>{section.description}</p> : null}
      </div>
      {blocks.length > 0 ? (
        <div className="vtqa-document-wrap">
          {blocks.map((block) => (
            <DocumentEvidenceBlock key={block.id} block={block} />
          ))}
        </div>
      ) : null}
      {tables.map((table) => (
        <EvidenceTable key={table.id} table={table} sectionTitle={section.title} />
      ))}
    </section>
  )
}

function EvidenceSectionList({ sections }: { sections: NormalizedEvidenceSection[] }) {
  if (sections.length === 0) {
    return (
      <section className="vtqa-empty-evidence">
        <Sparkles aria-hidden="true" />
        <h2>표시할 근거를 준비하는 중입니다.</h2>
      </section>
    )
  }
  return (
    <section className="vtqa-evidence" aria-label="근거 섹션">
      {sections.map((section) => (
        <EvidenceSection key={section.id} section={section} />
      ))}
    </section>
  )
}

function AnswerChoiceCard({
  choice,
  selected,
  disabled,
  onSelect,
}: {
  choice: NonNullable<NormalizedSampleViewModel['choices']>[number]
  selected: boolean
  disabled: boolean
  onSelect: (id: string) => void
}) {
  return (
    <button
      type="button"
      className="vtqa-choice-card"
      aria-pressed={selected}
      aria-label={choice.ariaLabel}
      disabled={disabled || choice.disabled}
      onClick={() => onSelect(choice.id)}
    >
      <span className="vtqa-choice-id">{choice.id}</span>
      <span className="vtqa-choice-value">{choice.displayValue}</span>
    </button>
  )
}

function AnswerChoiceGrid({
  model,
  answer,
  disabled,
  onAnswerChange,
}: {
  model: NormalizedSampleViewModel
  answer: string
  disabled: boolean
  onAnswerChange: (answer: string) => void
}) {
  if (!model.choices || model.choices.length === 0) {
    return null
  }

  return (
    <section className="vtqa-answers" aria-labelledby="answer-choice-heading">
      <div className="vtqa-inspector-heading">
        <h2 id="answer-choice-heading">답안 선택</h2>
      </div>
      <div className="vtqa-choice-grid">
        {model.choices.map((choice) => (
          <AnswerChoiceCard key={choice.id} choice={choice} selected={answer === choice.id || answer === choice.displayValue} disabled={disabled} onSelect={onAnswerChange} />
        ))}
      </div>
    </section>
  )
}

function AnswerSubmissionPanel({
  answer,
  isLoading,
  invalid,
  errorText,
  onAnswerChange,
  onSubmit,
}: {
  answer: string
  isLoading: boolean
  invalid: boolean
  errorText: string
  onAnswerChange: (answer: string) => void
  onSubmit: (answer: string) => void
}) {
  return (
    <Card className="vtqa-card vtqa-submit" data-testid="answer-card">
      <CardContent>
        <form
          className="vtqa-submit-row"
          onSubmit={(event) => {
            event.preventDefault()
            onSubmit(answer)
          }}
        >
          <input value={answer} onChange={(event) => onAnswerChange(event.target.value)} placeholder="예: A 또는 38원" disabled={isLoading || invalid} aria-label="정답 입력" />
          <Button type="submit" disabled={isLoading || invalid || !answer.trim()}>
            <Send className="mr-2 h-4 w-4" />
            제출
          </Button>
        </form>
        {errorText ? <p className="vtqa-error">{errorText}</p> : null}
      </CardContent>
    </Card>
  )
}

export function SampleViewer({ observation, info, answer, isLoading, errorText, renderMode = 'review', onAnswerChange, onSubmit }: SampleViewerProps) {
  const model = normalizeSampleViewModel(observation, info, renderMode)
  const defaultPageKey = useMemo(() => {
    const evidenceSection = model.evidenceSections.find((section) => 'pageKey' in section && Boolean(section.pageKey))
    const evidencePageKey = evidenceSection && 'pageKey' in evidenceSection ? evidenceSection.pageKey : undefined
    return evidencePageKey ?? model.pages.find((page) => page.active)?.key ?? model.pages[0]?.key ?? 'current'
  }, [model.evidenceSections, model.pages])
  const [activePageKey, setActivePageKey] = useState(defaultPageKey)
  useEffect(() => {
    setActivePageKey(defaultPageKey)
  }, [defaultPageKey])

  const blockingErrors = model.validationIssues.filter((issue) => issue.severity === 'error')
  const visibleIssues = blockingErrors
  const invalid = blockingErrors.length > 0
  const visibleSections = model.evidenceSections.filter((section) => !('pageKey' in section) || !section.pageKey || section.pageKey === activePageKey)

  return (
    <main className="vtqa-shell" data-render-mode={renderMode}>
      <PageHeader model={model} />
      <div className="vtqa-workspace">
        <section className="vtqa-document-pane" aria-label="근거 문서">
          <PageNavigation model={model} activePageKey={activePageKey} onSelect={setActivePageKey} />
          <div className="vtqa-canvas">
            <div className="vtqa-canvas-toolbar">
              <div>
                <p>근거 워크스페이스</p>
                <h2>{model.pages.find((page) => page.key === activePageKey)?.label ?? '근거 문서'}</h2>
              </div>
              <span>{model.pages.length > 0 ? `${model.pages.findIndex((page) => page.key === activePageKey) + 1}/${model.pages.length}` : '1/1'}</span>
            </div>
            <ValidationErrorState issues={visibleIssues} />
            {!invalid ? <EvidenceSectionList sections={visibleSections} /> : null}
          </div>
        </section>

        <aside className="vtqa-task-panel" aria-label="문제 풀이 패널">
          <QuestionCard model={model} />
          <SubmissionFormatCard model={model} />
          {!invalid ? <AnswerChoiceGrid model={model} answer={answer} onAnswerChange={onAnswerChange} disabled={isLoading} /> : null}
          {renderMode === 'review' ? (
            <AnswerSubmissionPanel answer={answer} isLoading={isLoading} invalid={invalid} errorText={errorText} onAnswerChange={onAnswerChange} onSubmit={onSubmit} />
          ) : null}
        </aside>
      </div>
    </main>
  )
}
