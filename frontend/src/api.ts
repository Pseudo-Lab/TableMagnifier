export type CatalogLevel = {
  level: number
  sample_episode_id: string
  sample_question: string
  max_actions: number
  page_count: number
  sheet_count: number
}

export type CatalogFamily = {
  family: string
  family_display_name: string
  levels: CatalogLevel[]
}

export type BenchmarkInstance = {
  instance_id: string
  instance_label: string
  family: string
  family_display_name: string
  level: number
  source_template_id: string
  source_seed: number
  source_episode_id: string
  task_summary: string
  decisive_evidence_surfaces: string[]
  expected_failure_mode: string
  question: string
  workbook_title: string
  max_actions: number
  sheet_count: number
  page_count: number
}

export type InstancePack = {
  pack_id: string
  pack_label: string
  version: string
  locale: string
  instance_count: number
  instances: BenchmarkInstance[]
}

export type Observation = {
  viewport_svg: string
  viewport_scene: Record<string, unknown>
  viewport_image_png_base64: string
  viewport_width: number
  viewport_height: number
  question: string
  remaining_action_budget: number
  current_sheet_name: string
  current_sheet_index: number
  current_page_index: number
  page_count_in_sheet: number
  sheet_tabs: string[]
  action_history_summary: string[]
}

export type Info = {
  episode_id: string
  family: string
  family_display_name: string
  level: number
  seed: number
  instance_id?: string | null
  instance_label?: string | null
  pack_id?: string | null
  locale: string
  mode: string
  workbook_title: string
  sheet_count: number
  sheet_tabs: string[]
  sheet_page_counts: number[]
  active_sheet: string
  active_sheet_index: number
  page_count_in_sheet: number
  current_page_index: number
  max_actions: number
  action_count: number
  unique_sheets_visited: number
  unique_pages_visited: number
  terminated: boolean
  truncated: boolean
  last_action?: Record<string, unknown>
  last_event?: Record<string, unknown>
}

export type ObservationEnvelope = {
  session_id: string
  observation: Observation
  info: Info
}

export type StepEnvelope = ObservationEnvelope & {
  reward: number
  terminated: boolean
  truncated: boolean
  submitted_answer: string | null
}

export type ReplayEnvelope = {
  session_id: string
  replay: {
    episode_id: string
    family: string
    level: number
    seed: number
    action_count: number
    events: Array<Record<string, unknown>>
  }
}

export type ActionPayload = {
  type: string
  x?: number
  y?: number
  sheet?: string | number
  text?: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Request failed: ${response.status}`)
  }

  return (await response.json()) as T
}

export function fetchCatalog() {
  return fetchJson<CatalogFamily[]>('/api/catalog')
}

export function fetchInstances() {
  return fetchJson<InstancePack[]>('/api/instances')
}

export function createSession(payload: {
  family?: string
  level?: number
  seed: number
  instance_id?: string
  mode?: string
  debug?: boolean
}) {
  return fetchJson<ObservationEnvelope>('/api/sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function stepSession(sessionId: string, payload: ActionPayload) {
  return fetchJson<StepEnvelope>(`/api/sessions/${sessionId}/actions`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchReplay(sessionId: string) {
  return fetchJson<ReplayEnvelope>(`/api/sessions/${sessionId}/replay`)
}
