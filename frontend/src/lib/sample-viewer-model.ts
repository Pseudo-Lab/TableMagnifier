import type { Info, Observation } from '@/api'

export type RenderMode = 'review' | 'evaluation'

type SceneRecord = Record<string, unknown>

type SceneCell = {
  row: number
  col: number
  text: string
  rowSpan: number
  colSpan: number
  align?: 'left' | 'center' | 'right'
}

type SceneTable = {
  elementId: string
  title: string
  sheetId?: string
  sheetName?: string
  pageId?: string
  pageTitle?: string
  nRows: number
  nCols: number
  cells: SceneCell[]
}

type SceneTextBlock = {
  elementId: string
  title: string
  sheetId?: string
  sheetName?: string
  pageId?: string
  pageTitle?: string
  lines: string[]
}

export type NormalizedValidationIssue = {
  severity: 'warning' | 'error'
  code: string
  title: string
  message: string
}

export type NormalizedTable = {
  id: string
  caption?: string
  columns: Array<{
    id: string
    label: string
    align?: 'left' | 'center' | 'right'
  }>
  rows: Array<{
    id: string
    label?: string
    cells: Array<{
      columnId: string
      value: string | number | null
      displayValue: string
      isUnknown?: boolean
      align?: 'left' | 'center' | 'right'
      colSpan?: number
      rowSpan?: number
      asHeader?: boolean
    }>
  }>
}

export type NormalizedTextBlock = {
  id: string
  type: 'paragraph' | 'note' | 'list' | 'keyValue'
  text?: string
  items?: string[]
  pairs?: Array<{ label: string; value: string }>
}

export type NormalizedEvidenceSection =
  | {
      id: string
      pageKey?: string
      kind: 'completed_rows' | 'query_row' | 'table'
      title: string
      description?: string
      tables: NormalizedTable[]
    }
  | {
      id: string
      pageKey?: string
      kind: 'document'
      title: string
      description?: string
      blocks: NormalizedTextBlock[]
    }
  | {
      id: string
      pageKey?: string
      kind: 'mixed'
      title: string
      description?: string
      tables?: NormalizedTable[]
      blocks?: NormalizedTextBlock[]
    }
  | {
      id: string
      kind: 'validation'
      title: string
      description?: string
      issues: NormalizedValidationIssue[]
    }

export type NormalizedSampleViewModel = {
  id?: string
  dataset?: string
  template?: string
  taskType?: string
  mode?: 'example' | 'query' | 'review' | 'evaluation'
  pageIndex?: number
  pageCount?: number
  pages: Array<{
    key: string
    label: string
    eyebrow?: string
    active?: boolean
  }>
  header: {
    title: string
    subtitle?: string
    badges?: Array<{
      label: string
      value?: string
      tone?: 'neutral' | 'accent' | 'warning' | 'danger'
    }>
  }
  question: {
    title: string
    text: string
  }
  submission: {
    title: string
    description?: string
    formats: Array<{ id: string; label: string }>
  }
  evidenceSections: NormalizedEvidenceSection[]
  choices?: Array<{
    id: string
    value: string | number
    displayValue: string
    ariaLabel?: string
    disabled?: boolean
  }>
  validationIssues: NormalizedValidationIssue[]
  debug?: unknown
}

export const FORBIDDEN_VISIBLE_STRINGS = [
  '검산 후보',
  '표 단서 적용 후보',
  '문서 단서 적용 후보',
  '단위 확인 후보',
  'candidate',
  'distractor',
  'rationale',
  'debug',
  'generation',
  'source_hint',
  'answer_type',
  'candidate_type',
  'distractor_type',
  'rationale_type',
] as const

const QUERY_ROW_RE = /(질의|query|미완성|확대해|적용 대상|대상 세기|원장|target)/i
const COMPLETED_ROWS_RE = /(완성|예시|example|examples|규칙 찾기|오프셋|마커 위치 규칙)/i
const QUESTION_REQUIRES_COMPLETED_RE = /(완성\s*(행|예시)|completed\s*rows?|example\s*rows?|규칙을\s*유도|유도했을\s*때|rule\s*induction|derive\s*the\s*rule|예시의|완성 예시)/i
const QUESTION_REQUIRES_QUERY_RE = /(질의\s*(행|표)|query\s*row|질의 표|미완성|적용하면|구하라|제출하라|얼마인가|몇\s*(개|점))/i

function asRecord(value: unknown): SceneRecord | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as SceneRecord) : null
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function asNumber(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

function cleanText(value: unknown): string {
  return asString(value).replace(/\s+/g, ' ').trim()
}

function containsForbiddenVisibleText(text: string) {
  const lower = text.toLowerCase()
  return FORBIDDEN_VISIBLE_STRINGS.some((token) => lower.includes(token.toLowerCase()))
}

function sceneElements(observation: Observation | null): SceneRecord[] {
  if (Array.isArray(observation?.sample_surfaces) && observation.sample_surfaces.length > 0) {
    return observation.sample_surfaces.flatMap((surface) =>
      (Array.isArray(surface.elements) ? surface.elements : [])
        .map(asRecord)
        .filter((element): element is SceneRecord => element !== null)
        .map((element): SceneRecord => ({
          ...element,
          __sheet_id: surface.sheet_id,
          __sheet_name: surface.sheet_name,
          __page_id: surface.page_id,
          __page_title: surface.page_title,
        })),
    )
  }

  const scene = asRecord(observation?.viewport_scene)
  const page = asRecord(scene?.page)
  const elements = Array.isArray(page?.elements) ? page.elements : []
  return elements.map(asRecord).filter((element): element is SceneRecord => element !== null)
}

function parseTables(observation: Observation | null): SceneTable[] {
  return sceneElements(observation)
    .filter((element) => element.type === 'table')
    .map((element) => ({
      elementId: cleanText(element.element_id),
      title: cleanText(element.title),
      sheetId: cleanText(element.__sheet_id),
      sheetName: cleanText(element.__sheet_name),
      pageId: cleanText(element.__page_id),
      pageTitle: cleanText(element.__page_title),
      nRows: asNumber(element.n_rows),
      nCols: asNumber(element.n_cols),
      cells: (Array.isArray(element.cells) ? element.cells : [])
        .map(asRecord)
        .filter((cell): cell is SceneRecord => cell !== null)
        .map((cell) => ({
          row: asNumber(cell.row),
          col: asNumber(cell.col),
          text: cleanText(cell.text),
          rowSpan: asNumber(cell.row_span) || 1,
          colSpan: asNumber(cell.col_span) || 1,
          align: parseAlign(cell.align),
        })),
    }))
}

function parseTextBlocks(observation: Observation | null): SceneTextBlock[] {
  return sceneElements(observation)
    .filter((element) => element.type === 'text_block')
    .map((element) => ({
      elementId: cleanText(element.element_id),
      title: cleanText(element.title),
      sheetId: cleanText(element.__sheet_id),
      sheetName: cleanText(element.__sheet_name),
      pageId: cleanText(element.__page_id),
      pageTitle: cleanText(element.__page_title),
      lines: (Array.isArray(element.lines) ? element.lines : []).map(cleanText).filter(Boolean),
    }))
}

function parseAlign(value: unknown): 'left' | 'center' | 'right' | undefined {
  const align = asString(value)
  return align === 'left' || align === 'center' || align === 'right' ? align : undefined
}

function isChoiceBlock(block: SceneTextBlock) {
  return block.elementId.startsWith('answer-') || /^선택지\s+[A-Z]$/.test(block.title)
}

function parseChoiceId(block: SceneTextBlock) {
  return (block.title.match(/선택지\s+([A-Z])/)?.[1] ?? block.elementId.match(/answer-([a-z])/i)?.[1]?.toUpperCase() ?? '').trim()
}

function normalizeChoices(blocks: SceneTextBlock[], issues: NormalizedValidationIssue[]) {
  return blocks
    .filter(isChoiceBlock)
    .map((block) => {
      const id = parseChoiceId(block)
      const displayValue = block.lines.find((line) => line && !containsForbiddenVisibleText(line)) ?? ''
      if (!id || !displayValue) {
        issues.push({
          severity: 'error',
          code: 'choice_missing_visible_value',
          title: '선택지 값 누락',
          message: `${block.title || block.elementId || '선택지'}에서 표시 가능한 선택지 ID 또는 값이 없습니다.`,
        })
        return null
      }
      if (block.lines.some(containsForbiddenVisibleText) || containsForbiddenVisibleText(block.title)) {
        issues.push({
          severity: 'error',
          code: 'choice_metadata_leak',
          title: '선택지 메타데이터 노출',
          message: `${id} 선택지에 내부 후보/근거 메타데이터로 보이는 문자열이 포함되어 제거했습니다.`,
        })
      }
      return {
        id,
        value: displayValue,
        displayValue,
        ariaLabel: `선택지 ${id}: ${displayValue}`,
      }
    })
    .filter((choice): choice is NonNullable<typeof choice> => choice !== null)
}

function normalizeTextBlock(block: SceneTextBlock): NormalizedTextBlock | null {
  const visibleLines = block.lines.filter((line) => !containsForbiddenVisibleText(line))
  if (visibleLines.length === 0 || containsForbiddenVisibleText(block.title)) {
    return null
  }
  return {
    id: block.elementId || block.title,
    type: block.title.includes('제출') ? 'note' : 'paragraph',
    text: visibleLines.join('\n'),
  }
}

function normalizeTable(table: SceneTable): NormalizedTable {
  const colIds = Array.from({ length: Math.max(table.nCols, 1) }, (_, index) => `c${index}`)
  const headerCells = table.cells.filter((cell) => cell.row === 0)
  const columns = colIds.map((id, index) => ({
    id,
    label: headerCells.find((cell) => cell.col === index)?.text || `열 ${index + 1}`,
    align: headerCells.find((cell) => cell.col === index)?.align,
  }))

  const rows = Array.from({ length: Math.max(table.nRows - 1, 0) }, (_, rowOffset) => {
    const rowIndex = rowOffset + 1
    const rowCells = table.cells
      .filter((cell) => cell.row === rowIndex)
      .sort((a, b) => a.col - b.col)
    const rowHeader = rowCells.find((cell) => cell.col === 0)
    return {
      id: `${table.elementId || table.title}-r${rowIndex}`,
      label: rowHeader?.text,
      cells: rowCells.map((cell) => ({
        columnId: colIds[cell.col] ?? `c${cell.col}`,
        value: cell.text || null,
        displayValue: cell.text || '미지정',
        isUnknown: ['?', '？', '', '미지정'].includes(cell.text),
        align: cell.align,
        colSpan: cell.colSpan > 1 ? cell.colSpan : undefined,
        rowSpan: cell.rowSpan > 1 ? cell.rowSpan : undefined,
        asHeader: cell.col === 0,
      })),
    }
  })

  return {
    id: [table.sheetId, table.pageId, table.elementId || table.title].filter(Boolean).join(':'),
    caption: table.title,
    columns,
    rows,
  }
}

function classifyTable(table: SceneTable, info: Info | null): 'completed_rows' | 'query_row' | 'table' {
  const key = `${table.elementId} ${table.title} ${table.sheetId ?? info?.active_sheet_id ?? ''} ${table.pageId ?? info?.current_page_id ?? ''}`
  if (COMPLETED_ROWS_RE.test(key) || /completed/.test(key.toLowerCase())) {
    return 'completed_rows'
  }
  if (QUERY_ROW_RE.test(key)) {
    return 'query_row'
  }
  return 'table'
}

function sectionTitle(kind: 'completed_rows' | 'query_row' | 'table', table: SceneTable) {
  if (kind === 'completed_rows') {
    return '완성 행'
  }
  if (kind === 'query_row') {
    return '질의 행'
  }
  return table.title || '근거 표'
}

function sectionDescription(kind: 'completed_rows' | 'query_row' | 'table', table: SceneTable) {
  if (table.pageTitle && table.pageTitle !== table.title) {
    return table.pageTitle
  }
  if (kind === 'completed_rows') {
    return '규칙 유도와 적용 범위 확인에 필요한 예시 근거입니다.'
  }
  if (kind === 'query_row') {
    return '최종 질문에 답하기 위해 규칙을 적용할 대상입니다.'
  }
  return '질문 해결에 필요한 표 근거입니다.'
}

function normalizeEvidenceSections(tables: SceneTable[], blocks: SceneTextBlock[], info: Info | null) {
  const sections: NormalizedEvidenceSection[] = []
  const nonChoiceBlocks = blocks.filter((block) => !isChoiceBlock(block) && block.elementId !== 'query-target' && block.elementId !== 'query-guidance')
  const documentBlocks = nonChoiceBlocks.map(normalizeTextBlock).filter((block): block is NormalizedTextBlock => block !== null)

  for (const table of tables) {
    const kind = classifyTable(table, info)
    sections.push({
      id: [table.sheetId, table.pageId, table.elementId || `${kind}-${sections.length}`].filter(Boolean).join(':'),
      pageKey: pageKey(table.sheetId || info?.active_sheet_id, table.pageId || info?.current_page_id),
      kind,
      title: sectionTitle(kind, table),
      description: sectionDescription(kind, table),
      tables: [normalizeTable(table)],
    })
  }

  if (documentBlocks.length > 0) {
    const firstBlock = nonChoiceBlocks[0]
    sections.push({
      id: 'document-evidence',
      pageKey: pageKey(firstBlock?.sheetId || info?.active_sheet_id, firstBlock?.pageId || info?.current_page_id),
      kind: 'document',
      title: '문서 근거',
      description: '질문 해결에 필요한 문서 또는 주석 근거입니다.',
      blocks: documentBlocks,
    })
  }

  return sections
}

function pageKey(sheetId: string | undefined, pageId: string | undefined) {
  return [sheetId, pageId].filter(Boolean).join(':') || 'current'
}

function naturalPageLabel(value: string, fallback: string) {
  const text = cleanText(value) || fallback
  const lower = text.toLowerCase()
  if (/abbrev|glossary|약어/.test(lower) || /약어/.test(text)) {
    return '약어집'
  }
  if (/note|manual|reference|doc|참고|문서/.test(lower) || /참고|문서|안내/.test(text)) {
    return '참고 문서'
  }
  if (/calc|rule|criteria|기준|계산/.test(lower) || /계산|기준|규칙/.test(text)) {
    return '계산 기준'
  }
  if (/query|질의|target/.test(lower) || /질의|대상/.test(text)) {
    return '워크시트'
  }
  if (/detail|wide|상세/.test(lower) || /상세|확장/.test(text)) {
    return '상세 표'
  }
  if (/main|overview|메인/.test(lower) || /메인|원장/.test(text)) {
    return '메인 표'
  }
  return text
}

function normalizePages(observation: Observation | null, info: Info | null) {
  if (Array.isArray(observation?.sample_surfaces) && observation.sample_surfaces.length > 0) {
    return observation.sample_surfaces.map((surface, index) => ({
      key: pageKey(surface.sheet_id, surface.page_id),
      label: naturalPageLabel(surface.page_title || surface.sheet_name, `페이지 ${index + 1}`),
      eyebrow: surface.sheet_name,
      active: info ? surface.sheet_name === info.active_sheet && surface.page_id === info.current_page_id : index === 0,
    }))
  }

  if (info) {
    return info.sheet_tabs.map((sheet, index) => ({
      key: pageKey(index === info.active_sheet_index ? info.active_sheet_id : sheet, index === info.active_sheet_index ? info.current_page_id : undefined),
      label: naturalPageLabel(sheet, `문서 ${index + 1}`),
      eyebrow: info.sheet_page_counts[index] ? `${info.sheet_page_counts[index]}쪽` : undefined,
      active: sheet === info.active_sheet,
    }))
  }

  return []
}

function inferSubmissionFormats(question: string, guidanceBlocks: SceneTextBlock[], choices: Array<{ id: string }>) {
  const guidance = guidanceBlocks.flatMap((block) => block.lines).join(' ')
  const source = `${question} ${guidance}`
  const formats = []
  if (choices.length > 0 || /선택지\s*ID/i.test(source)) {
    formats.push({ id: 'choice_id', label: '선택지 ID' })
  }
  if (/원/.test(source)) {
    formats.push({ id: 'krw', label: '원 단위 숫자' })
  } else if (/점|%p|퍼센트포인트/.test(source)) {
    formats.push({ id: 'points', label: '점 단위 숫자' })
  } else if (/개/.test(source)) {
    formats.push({ id: 'count', label: '개수' })
  } else {
    formats.push({ id: 'text', label: '짧은 답' })
  }
  return formats
}

function addValidation(model: NormalizedSampleViewModel, tables: SceneTable[]) {
  const issues = [...model.validationIssues]
  const question = model.question.text
  const hasCompleted = model.evidenceSections.some((section) => section.kind === 'completed_rows')
  const hasQuery = model.evidenceSections.some((section) => section.kind === 'query_row')
  const requiredRefs = Array.isArray(model.debug) ? [] : []
  void requiredRefs

  if (!question) {
    issues.push({ severity: 'error', code: 'question_missing', title: '질문 누락', message: '표시할 최종 질문이 없습니다.' })
  }
  if (model.submission.formats.length === 0) {
    issues.push({ severity: 'error', code: 'submission_missing', title: '제출 형식 누락', message: '정답 제출 형식을 확인할 수 없습니다.' })
  }
  if (model.evidenceSections.length === 0) {
    issues.push({ severity: 'error', code: 'evidence_missing', title: '근거 누락', message: '현재 샘플 화면에 표시 가능한 표 또는 문서 근거가 없습니다.' })
  }
  if (QUESTION_REQUIRES_COMPLETED_RE.test(question) && !hasCompleted) {
    issues.push({
      severity: 'error',
      code: 'completed_rows_missing',
      title: '완성/예시 근거 누락',
      message: '질문이 완성 행 또는 예시 규칙 유도를 요구하지만 현재 화면에서 해당 근거 섹션을 찾지 못했습니다.',
    })
  }
  if (QUESTION_REQUIRES_QUERY_RE.test(question) && !hasQuery && tables.length > 0 && model.choices && model.choices.length > 0) {
    issues.push({
      severity: 'warning',
      code: 'query_row_not_explicit',
      title: '질의 행 섹션 확인 필요',
      message: '질문이 질의 대상을 요구하지만 현재 표 제목에서 명시적인 질의 행을 찾지 못했습니다.',
    })
  }
  if (!model.choices || model.choices.length === 0) {
    issues.push({ severity: 'warning', code: 'choices_missing', title: '선택지 없음', message: '현재 페이지에서 표시 가능한 A/B/C/D 선택지를 찾지 못했습니다.' })
  }
  for (const choice of model.choices ?? []) {
    if (!choice.id || !choice.displayValue) {
      issues.push({ severity: 'error', code: 'choice_invalid', title: '선택지 형식 오류', message: '선택지는 ID와 표시값을 모두 가져야 합니다.' })
    }
    if (containsForbiddenVisibleText(`${choice.id} ${choice.displayValue}`)) {
      issues.push({ severity: 'error', code: 'choice_metadata_leak', title: '선택지 메타데이터 노출', message: '선택지 표시값에 내부 메타데이터 문자열이 포함되어 있습니다.' })
    }
  }
  for (const section of model.evidenceSections) {
    if ('tables' in section && section.tables) {
      for (const table of section.tables) {
        if (table.columns.length === 0 || table.rows.length === 0) {
          issues.push({ severity: 'error', code: 'table_empty', title: '표 구조 오류', message: `${table.caption ?? table.id} 표에 열 또는 행이 없습니다.` })
        }
      }
    }
  }

  return issues
}

function adapterName(templateId: string | null | undefined) {
  if (templateId === 'symbol_rule_induction' || templateId === 'color_condition_rule_induction') {
    return 'rule_induction_adapter'
  }
  if (templateId === 'abbrev_doc_reference' || templateId === 'legend_color_exception_scope') {
    return 'document_table_adapter'
  }
  if (templateId === 'wide_table_navigation' || templateId === 'wide_table_viewport_trace' || templateId === 'merged_header_pan_scope') {
    return 'wide_table_adapter'
  }
  if (templateId === 'merged_header_scope' || templateId === 'zoom_micro_marker_exception') {
    return 'structured_table_adapter'
  }
  return 'generic_scene_adapter'
}

export function normalizeSampleViewModel(observation: Observation | null, info: Info | null, renderMode: RenderMode = 'review'): NormalizedSampleViewModel {
  const issues: NormalizedValidationIssue[] = []
  const tables = parseTables(observation)
  const textBlocks = parseTextBlocks(observation)
  const choices = normalizeChoices(textBlocks, issues)
  const guidanceBlocks = textBlocks.filter((block) => block.elementId === 'query-guidance' || block.title === '제출 형식')
  const question = cleanText(observation?.question) || textBlocks.find((block) => block.elementId === 'query-target')?.lines.join(' ') || ''
  const evidenceSections = normalizeEvidenceSections(tables, textBlocks, info)
  const pages = normalizePages(observation, info)
  const model: NormalizedSampleViewModel = {
    id: info?.episode_id,
    dataset: info?.family_display_name ?? info?.family ?? undefined,
    template: info?.template_id ?? undefined,
    taskType: adapterName(info?.template_id),
    mode: renderMode,
    pageIndex: info ? info.current_page_index + 1 : undefined,
    pageCount: info?.page_count_in_sheet,
    pages,
    header: {
      title: info?.workbook_title || info?.family_display_name || 'Visual TableQA',
      subtitle: info ? `${info.active_sheet} · ${info.current_page_index + 1}/${info.page_count_in_sheet}쪽` : '샘플을 준비하는 중입니다.',
      badges: [
        { label: '문서 QA', tone: 'accent' as const },
        info?.level ? { label: `레벨 ${info.level}` } : null,
        pages.length > 0 ? { label: `${pages.length}쪽 문서` } : info ? { label: `${info.current_page_index + 1}/${info.page_count_in_sheet}쪽` } : null,
      ].filter((badge): badge is NonNullable<typeof badge> => badge !== null),
    },
    question: {
      title: '최종 질문',
      text: question,
    },
    submission: {
      title: '정답 제출 형식',
      description: guidanceBlocks.flatMap((block) => block.lines).join(' ') || '정답은 지정된 형식으로 제출합니다.',
      formats: inferSubmissionFormats(question, guidanceBlocks, choices),
    },
    evidenceSections,
    choices,
    validationIssues: issues,
    debug: {
      adapter: adapterName(info?.template_id),
      activeSheetId: info?.active_sheet_id,
      requiredPageRefs: info?.required_navigation?.required_page_refs,
    },
  }

  return {
    ...model,
    validationIssues: addValidation(model, tables),
  }
}
