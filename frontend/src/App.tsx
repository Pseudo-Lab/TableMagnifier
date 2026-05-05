import { useEffect, useEffectEvent, useMemo, useRef, useState } from 'react'
import { Activity, ChevronLeft, ChevronRight, Crosshair, Eye, LayoutPanelLeft, PanelRight, RefreshCw, Search, Send, ZoomIn, ZoomOut } from 'lucide-react'

import { EventFeed, InfoGrid } from '@/components/workbench/event-feed'
import { WorkbookCanvas } from '@/components/workbench/workbook-canvas'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  createSession,
  fetchCatalog,
  fetchInstances,
  fetchReplay,
  stepSession,
  type ActionPayload,
  type CatalogFamily,
  type Info,
  type InstancePack,
  type Observation,
} from '@/api'

type EventRecord = Record<string, unknown>
type InspectorTab = 'session' | 'log' | 'replay' | 'help'

const numberFormatter = new Intl.NumberFormat('ko-KR')

const actionLabels: Record<string, string> = {
  select_sheet: '시트 전환',
  zoom_in: '확대',
  zoom_out: '축소',
  pan_up: '위로 이동',
  pan_down: '아래로 이동',
  pan_left: '왼쪽 이동',
  pan_right: '오른쪽 이동',
  click_region: '뷰포트 클릭',
  next_page: '다음 페이지',
  prev_page: '이전 페이지',
  submit_answer: '정답 제출',
}

function asRecord(value: unknown): EventRecord | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as EventRecord) : null
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' ? value : null
}

function asString(value: unknown): string | null {
  return typeof value === 'string' ? value : null
}

function formatInteger(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return '-'
  }
  return numberFormatter.format(value)
}

function familyStatusSuffix(family: CatalogFamily) {
  if (family.is_preferred) {
    return ' · 우선'
  }
  if (family.family_status === 'deprecated') {
    return ' · deprecated'
  }
  if (family.family_status === 'active') {
    return ' · active'
  }
  return ''
}

function familyStatusLabel(family: CatalogFamily | null) {
  if (!family) {
    return '-'
  }
  if (family.is_preferred) {
    return 'preferred'
  }
  return family.family_status || 'active'
}

function requestedDevSession(catalog: CatalogFamily[]) {
  const params = new URLSearchParams(window.location.search)
  const familyParam = params.get('family')
  if (!familyParam) {
    return null
  }

  const family = catalog.find((item) => item.family === familyParam)
  if (!family) {
    return null
  }

  const levelParam = params.get('level')
  const level = levelParam === null ? family.levels[0]?.level : Number(levelParam)
  if (!Number.isInteger(level) || !family.levels.some((item) => item.level === level)) {
    return null
  }

  const seedParam = params.get('seed')
  const seed = seedParam === null ? 0 : Number(seedParam)
  return {
    family: family.family,
    level,
    seed: Number.isFinite(seed) ? seed : 0,
  }
}

function describeAction(event: EventRecord) {
  const action = asRecord(event.action)
  if (!action) {
    return '알 수 없는 액션'
  }

  const type = asString(action.type) ?? 'unknown'
  if (type === 'click_region') {
    return `뷰포트 클릭 (${formatInteger(asNumber(action.x))}, ${formatInteger(asNumber(action.y))})`
  }
  if (type === 'select_sheet') {
    return `시트 전환: ${asString(action.sheet) ?? '-'}`
  }
  if (type === 'submit_answer') {
    return `정답 제출: ${asString(action.text) ?? ''}`
  }
  return actionLabels[type] ?? type
}

function describeEventDetail(event: EventRecord) {
  const metadata = asRecord(event.metadata)
  const after = asRecord(event.after)
  const target = asRecord(metadata?.resolved_region)
  const reward = asNumber(event.reward)
  const sheetName = asString(after?.sheet_name)
  const pageIndex = asNumber(after?.page_index)
  const terminated = event.terminated === true
  const truncated = event.truncated === true

  const parts: string[] = []
  if (target) {
    const label = asString(target.label) ?? asString(target.public_id)
    const role = asString(target.role)
    if (label) {
      parts.push(role ? `대상 영역: ${label} (${role})` : `대상 영역: ${label}`)
    }
  }

  const openedNote = asString(metadata?.opened_note)
  if (openedNote) {
    parts.push(`열린 메모: ${openedNote}`)
  }

  if (pageIndex !== null) {
    parts.push(sheetName ? `${sheetName} 페이지 ${pageIndex + 1}` : `페이지 ${pageIndex + 1}`)
  }

  if (reward !== null && reward > 0) {
    parts.push(`reward ${reward.toFixed(3)}`)
  }

  if (terminated) {
    parts.push('에피소드 종료')
  } else if (truncated) {
    parts.push('예산 초과로 종료')
  }

  return parts.join(' · ') || '추가 메타데이터 없음'
}

function App() {
  const [catalog, setCatalog] = useState<CatalogFamily[]>([])
  const [instancePacks, setInstancePacks] = useState<InstancePack[]>([])
  const [selectedPackId, setSelectedPackId] = useState('')
  const [selectedInstanceId, setSelectedInstanceId] = useState('')
  const [selectedFamily, setSelectedFamily] = useState('')
  const [selectedLevel, setSelectedLevel] = useState(1)
  const [seed, setSeed] = useState(0)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [observation, setObservation] = useState<Observation | null>(null)
  const [info, setInfo] = useState<Info | null>(null)
  const [answer, setAnswer] = useState('')
  const [statusText, setStatusText] = useState('세션을 불러오는 중입니다.')
  const [errorText, setErrorText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [events, setEvents] = useState<EventRecord[]>([])
  const [replay, setReplay] = useState<EventRecord[]>([])
  const [lastClick, setLastClick] = useState<{ x: number; y: number } | null>(null)
  const [isInspectorOpen, setIsInspectorOpen] = useState(false)
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>('log')
  const viewerRef = useRef<HTMLDivElement | null>(null)
  const hasInitializedRef = useRef(false)

  const packRecord = instancePacks.find((item) => item.pack_id === selectedPackId) ?? null
  const instanceRecord = packRecord?.instances.find((item) => item.instance_id === selectedInstanceId) ?? null
  const familyRecord = catalog.find((item) => item.family === selectedFamily) ?? null
  const levelRecord = familyRecord?.levels.find((item) => item.level === selectedLevel) ?? null
  const latestEvent = events.length > 0 ? events[events.length - 1] : null
  const currentPageLabel = observation ? `${observation.current_page_index + 1}/${observation.page_count_in_sheet}` : '-/-'
  const sessionStateLabel = info?.terminated ? '정답 제출 완료' : info?.truncated ? '예산 종료' : '진행 중'
  const budgetLabel = observation ? `${observation.remaining_action_budget}회 남음` : '-'
  const latestActionLabel = latestEvent ? describeAction(latestEvent) : '아직 액션이 없습니다.'
  const viewboxData = info ? JSON.stringify(info.viewbox) : ''
  const initializeOnMount = useEffectEvent(() => {
    void initialize()
  })
  const applyHotkeyAction = useEffectEvent((payload: ActionPayload) => {
    void applyAction(payload)
  })

  useEffect(() => {
    if (hasInitializedRef.current) {
      return
    }
    hasInitializedRef.current = true
    initializeOnMount()
  }, [initializeOnMount])

  useEffect(() => {
    if (!packRecord) {
      return
    }

    const hasSelectedInstance = packRecord.instances.some((item) => item.instance_id === selectedInstanceId)
    if (!hasSelectedInstance) {
      setSelectedInstanceId(packRecord.instances[0]?.instance_id ?? '')
    }
  }, [packRecord, selectedInstanceId])

  useEffect(() => {
    if (!familyRecord) {
      return
    }

    const hasSelectedLevel = familyRecord.levels.some((item) => item.level === selectedLevel)
    if (!hasSelectedLevel) {
      setSelectedLevel(familyRecord.levels[0]?.level ?? 1)
    }
  }, [familyRecord, selectedLevel])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!sessionId || !info || info.terminated || info.truncated) {
        return
      }

      const target = event.target as HTMLElement | null
      const tagName = target?.tagName?.toLowerCase()
      if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') {
        return
      }

      const actionMap: Record<string, ActionPayload> = {
        ArrowUp: { type: 'pan_up' },
        ArrowDown: { type: 'pan_down' },
        ArrowLeft: { type: 'pan_left' },
        ArrowRight: { type: 'pan_right' },
        w: { type: 'pan_up' },
        s: { type: 'pan_down' },
        a: { type: 'pan_left' },
        d: { type: 'pan_right' },
        '+': { type: 'zoom_in' },
        '=': { type: 'zoom_in' },
        '-': { type: 'zoom_out' },
        '[': { type: 'prev_page' },
        ']': { type: 'next_page' },
      }

      if (event.key in actionMap) {
        event.preventDefault()
        applyHotkeyAction(actionMap[event.key])
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [sessionId, info, applyHotkeyAction])

  async function initialize() {
    setIsLoading(true)
    setErrorText('')
    try {
      const [nextCatalog, nextPacks] = await Promise.all([fetchCatalog(), fetchInstances()])
      setCatalog(nextCatalog)
      setInstancePacks(nextPacks)
      const initialFamily = nextCatalog[0]
      const initialLevel = initialFamily?.levels[0]?.level ?? 1
      if (initialFamily) {
        setSelectedFamily(initialFamily.family)
        setSelectedLevel(initialLevel)
      }

      const requestedSession = requestedDevSession(nextCatalog)
      if (requestedSession) {
        setSelectedFamily(requestedSession.family)
        setSelectedLevel(requestedSession.level)
        setSeed(requestedSession.seed)
        await startFamilySession(requestedSession.family, requestedSession.level, requestedSession.seed)
        return
      }

      const initialPack = nextPacks[0]
      const initialInstance = initialPack?.instances[0]
      if (initialPack && initialInstance) {
        setSelectedPackId(initialPack.pack_id)
        setSelectedInstanceId(initialInstance.instance_id)
        await startInstanceSession(initialInstance.instance_id)
      } else {
        if (!initialFamily) {
          return
        }
        await startFamilySession(initialFamily.family, initialLevel, 0)
      }
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : '카탈로그를 불러오지 못했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  async function startFamilySession(family: string, level: number, nextSeed: number) {
    setIsLoading(true)
    setErrorText('')
    setStatusText('새 세션을 준비하는 중입니다.')
    setEvents([])
    setReplay([])
    try {
      const response = await createSession({ family, level, seed: nextSeed, mode: 'human' })
      setSessionId(response.session_id)
      setObservation(response.observation)
      setInfo(response.info)
      setAnswer('')
      setLastClick(null)
      setStatusText(`${response.info.family_display_name} 레벨 ${response.info.level} 세션이 준비되었습니다.`)
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : '세션 생성에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  async function startInstanceSession(instanceId: string) {
    setIsLoading(true)
    setErrorText('')
    setStatusText('벤치마크 인스턴스를 준비하는 중입니다.')
    setEvents([])
    setReplay([])
    try {
      const response = await createSession({ instance_id: instanceId, seed: 0, mode: 'human' })
      setSessionId(response.session_id)
      setObservation(response.observation)
      setInfo(response.info)
      setAnswer('')
      setLastClick(null)
      setStatusText(`${response.info.instance_label ?? response.info.family_display_name} 세션이 준비되었습니다.`)
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : '세션 생성에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  async function loadReplay(nextSessionId: string) {
    try {
      const replayResponse = await fetchReplay(nextSessionId)
      setReplay(replayResponse.replay.events)
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : '리플레이를 불러오지 못했습니다.')
    }
  }

  async function applyAction(payload: ActionPayload) {
    if (!sessionId) {
      return
    }

    setIsLoading(true)
    setErrorText('')
    try {
      const response = await stepSession(sessionId, payload)
      setObservation(response.observation)
      setInfo(response.info)
      if (response.info.last_event) {
        setEvents((current) => [...current, response.info.last_event as EventRecord])
      }
      setStatusText(`reward ${response.reward.toFixed(3)} · 남은 예산 ${response.observation.remaining_action_budget} · 페이지 ${response.observation.current_page_index + 1}`)
      if (response.terminated || response.truncated) {
        await loadReplay(sessionId)
      }
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : '액션 실행에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  async function openInspector(tab: InspectorTab) {
    setInspectorTab(tab)
    setIsInspectorOpen(true)
    if (tab === 'replay' && sessionId && replay.length === 0) {
      await loadReplay(sessionId)
    }
  }

  function handleViewerClick(event: React.MouseEvent<HTMLDivElement>) {
    if (!viewerRef.current || !observation) {
      return
    }

    const clickTarget = viewerRef.current.querySelector('canvas') ?? viewerRef.current
    const bounds = clickTarget.getBoundingClientRect()
    const relativeX = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width))
    const relativeY = Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height))
    const x = Math.round(relativeX * observation.viewport_width)
    const y = Math.round(relativeY * observation.viewport_height)
    setLastClick({ x, y })
    void applyAction({ type: 'click_region', x, y })
  }

  const summaryItems = useMemo(
    () => [
      { label: '액션 수', value: info?.action_count ?? 0 },
      { label: '최근 클릭', value: lastClick ? `${lastClick.x}, ${lastClick.y}` : '-' },
      { label: '활성 시트', value: info?.active_sheet ?? '-' },
      { label: '최근 액션', value: latestEvent ? describeAction(latestEvent) : '-' },
    ],
    [info, lastClick, latestEvent],
  )

  const inspectorItems = useMemo(
    () => [
      { label: '에피소드', value: info?.episode_id ?? '-' },
      { label: '문제 세트', value: info?.pack_id ?? '-' },
      { label: '인스턴스', value: info?.instance_label ?? '-' },
      { label: '로케일', value: info?.locale ?? 'ko-KR' },
      { label: '샘플 에피소드', value: levelRecord?.sample_episode_id ?? '-' },
      { label: '방문한 시트 수', value: info?.unique_sheets_visited ?? 0 },
      { label: '방문한 페이지 수', value: info?.unique_pages_visited ?? 0 },
      { label: '마지막 액션', value: latestEvent ? describeAction(latestEvent) : '-' },
    ],
    [info, levelRecord, latestEvent],
  )

  return (
    <div className="min-h-screen bg-transparent">
      <div className="container max-w-[1840px] py-5 3xl:max-w-[2360px]">
        <div className="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)_400px] 3xl:grid-cols-[360px_minmax(0,1fr)_460px] 3xl:gap-6">
          <div className="space-y-6">
            <Card className="border-border/70 bg-card/95 shadow-soft">
              <CardHeader className="space-y-4">
                <div className="flex items-center justify-between">
                  <Badge variant="secondary" className="gap-1 rounded-full px-3 py-1">
                    <LayoutPanelLeft className="h-3.5 w-3.5" />
                    table-env-bench
                  </Badge>
                  <Badge variant={isLoading ? 'default' : 'outline'}>{sessionStateLabel}</Badge>
                </div>
                <div className="space-y-2">
                  <CardTitle className="text-2xl">한국어 Visual TableQA Workbench</CardTitle>
                  <CardDescription className="text-sm leading-6">{statusText}</CardDescription>
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="space-y-3">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">벤치마크 세트</label>
                    <select
                      data-testid="instance-pack-select"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={selectedPackId}
                      onChange={(event) => setSelectedPackId(event.target.value)}
                      disabled={isLoading || instancePacks.length === 0}
                    >
                      {instancePacks.map((pack) => (
                        <option key={pack.pack_id} value={pack.pack_id}>
                          {pack.pack_label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">고정 문제</label>
                    <select
                      data-testid="instance-select"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={selectedInstanceId}
                      onChange={(event) => setSelectedInstanceId(event.target.value)}
                      disabled={isLoading || !packRecord}
                    >
                      {(packRecord?.instances ?? []).map((instance) => (
                        <option key={instance.instance_id} value={instance.instance_id}>
                          {instance.instance_label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {instanceRecord ? (
                    <div className="rounded-lg border border-border/70 bg-muted/30 px-4 py-3 text-sm leading-6">
                      <p className="font-medium text-foreground">{instanceRecord.task_summary}</p>
                      <p className="mt-1 text-muted-foreground">
                        {instanceRecord.family_display_name} · 레벨 {instanceRecord.level} · {instanceRecord.page_count}페이지
                      </p>
                    </div>
                  ) : null}

                  <Button
                    data-testid="start-instance-button"
                    className="w-full gap-2"
                    onClick={() => void startInstanceSession(selectedInstanceId)}
                    disabled={!selectedInstanceId || isLoading}
                  >
                    <RefreshCw className="h-4 w-4" />
                    벤치마크 문제 시작
                  </Button>
                </div>

                <Separator />

                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <label className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">개발용 패밀리</label>
                    <Badge data-testid="family-status-badge" variant={familyRecord?.is_preferred ? 'secondary' : familyRecord?.family_status === 'deprecated' ? 'outline' : 'default'}>
                      {familyStatusLabel(familyRecord)}
                    </Badge>
                  </div>
                  <select
                    data-testid="family-select"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={selectedFamily}
                    onChange={(event) => setSelectedFamily(event.target.value)}
                    disabled={isLoading}
                  >
                    {catalog.map((family) => (
                      <option key={family.family} value={family.family}>
                        {family.family_display_name}
                        {familyStatusSuffix(family)}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">레벨</label>
                    <select
                      data-testid="level-select"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={selectedLevel}
                      onChange={(event) => setSelectedLevel(Number(event.target.value))}
                      disabled={isLoading}
                    >
                      {(familyRecord?.levels ?? []).map((level) => (
                        <option key={level.level} value={level.level}>
                          레벨 {level.level}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">시드</label>
                    <Input data-testid="seed-input" type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} disabled={isLoading} />
                  </div>
                </div>

                <Button data-testid="start-session-button" className="w-full gap-2" onClick={() => void startFamilySession(selectedFamily, selectedLevel, seed)} disabled={!selectedFamily || isLoading}>
                  <RefreshCw className="h-4 w-4" />
                  개발 세션 시작
                </Button>
              </CardContent>
            </Card>

            <Card className="border-border/70 shadow-soft">
              <CardHeader className="pb-4">
                <CardTitle className="text-base">현재 상태</CardTitle>
                <CardDescription>플레이에 필요한 상태만 먼저 보여주고, 자세한 기록은 Inspector에서 확인합니다.</CardDescription>
              </CardHeader>
              <CardContent>
                <InfoGrid items={summaryItems} />
              </CardContent>
            </Card>

            <Card className="border-border/70 shadow-soft">
              <CardHeader className="pb-4">
                <CardTitle className="text-base">탐색 컨트롤</CardTitle>
                <CardDescription>자주 쓰는 이동 동작만 노출합니다.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                {info ? (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">시트</p>
                    <div className="flex flex-wrap gap-2">
                      {info.sheet_tabs.map((sheet) => (
                        <Button
                          key={sheet}
                          data-testid="sheet-tab-button"
                          data-sheet-name={sheet}
                          variant={info.active_sheet === sheet ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => void applyAction({ type: 'select_sheet', sheet })}
                          disabled={isLoading || info.active_sheet === sheet}
                        >
                          {sheet}
                        </Button>
                      ))}
                    </div>
                  </div>
                ) : null}

                <Separator />

                <div className="grid grid-cols-2 gap-3">
                  <Button data-testid="prev-page-button" variant="outline" onClick={() => void applyAction({ type: 'prev_page' })} disabled={isLoading}>
                    <ChevronLeft className="h-4 w-4" />
                    이전 페이지
                  </Button>
                  <Button data-testid="next-page-button" variant="outline" onClick={() => void applyAction({ type: 'next_page' })} disabled={isLoading}>
                    다음 페이지
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" onClick={() => void applyAction({ type: 'zoom_in' })} disabled={isLoading}>
                    <ZoomIn className="h-4 w-4" />
                    확대
                  </Button>
                  <Button variant="outline" onClick={() => void applyAction({ type: 'zoom_out' })} disabled={isLoading}>
                    <ZoomOut className="h-4 w-4" />
                    축소
                  </Button>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div />
                  <Button variant="secondary" onClick={() => void applyAction({ type: 'pan_up' })} disabled={isLoading}>
                    ↑
                  </Button>
                  <div />
                  <Button variant="secondary" onClick={() => void applyAction({ type: 'pan_left' })} disabled={isLoading}>
                    ←
                  </Button>
                  <Button variant="outline" onClick={() => setLastClick(null)} disabled={isLoading}>
                    초기화
                  </Button>
                  <Button variant="secondary" onClick={() => void applyAction({ type: 'pan_right' })} disabled={isLoading}>
                    →
                  </Button>
                  <div />
                  <Button variant="secondary" onClick={() => void applyAction({ type: 'pan_down' })} disabled={isLoading}>
                    ↓
                  </Button>
                  <div />
                </div>
              </CardContent>
            </Card>
          </div>

          <main className="space-y-6">
            <Card className="border-border/70 bg-card/95 shadow-soft" data-testid="question-card">
              <CardHeader className="pb-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-2">
                    <Badge variant="outline" className="rounded-full px-3 py-1">
                      <Search className="mr-1 h-3.5 w-3.5" />
                      현재 질문
                    </Badge>
                    <CardTitle className="text-xl">{info?.instance_label ?? info?.family_display_name ?? '표 뷰어'}</CardTitle>
                    <CardDescription className="max-w-3xl text-sm leading-6">
                      {observation?.question ?? '세션이 준비되면 이 영역에 현재 질문이 표시됩니다.'}
                    </CardDescription>
                  </div>
                  <div className="flex flex-wrap justify-end gap-2">
                    <Badge data-testid="page-label" variant="secondary">{info ? `${info.active_sheet} · ${currentPageLabel}` : '세션 준비 중'}</Badge>
                    <Badge variant="outline">{budgetLabel}</Badge>
                    <Badge variant="outline">{latestActionLabel}</Badge>
                  </div>
                </div>
              </CardHeader>
            </Card>

            <Card className="viewer-panel border-border/70 bg-card/95 shadow-soft" data-testid="viewer-panel">
              <CardHeader className="pb-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-2">
                    <CardTitle className="flex items-center gap-2 text-xl">
                      <Eye className="h-5 w-5 text-primary" />
                      Workbook Viewport
                    </CardTitle>
                    <CardDescription>표를 직접 클릭해 탐색합니다. 상세 로그와 메타데이터는 오른쪽 Inspector에서 확인합니다.</CardDescription>
                  </div>
                  <Button variant={isInspectorOpen ? 'default' : 'outline'} onClick={() => void openInspector(inspectorTab)}>
                    <PanelRight className="mr-2 h-4 w-4" />
                    {isInspectorOpen ? 'Inspector 열림' : 'Inspector 열기'}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div
                  className="viewer-surface relative min-h-[760px] overflow-hidden rounded-xl border border-border bg-muted/20 p-4 shadow-inner"
                  data-testid="viewer-surface"
                  data-active-sheet-id={info?.active_sheet_id ?? ''}
                  data-current-page-id={info?.current_page_id ?? ''}
                  data-zoom-index={info?.zoom_index ?? 0}
                  data-viewbox={viewboxData}
                  ref={viewerRef}
                  onClick={handleViewerClick}
                >
                  <div className="overflow-hidden rounded-lg bg-white">
                    <WorkbookCanvas scene={observation?.viewport_scene ?? null} />
                  </div>
                </div>

                <div className="flex items-center justify-between gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Crosshair className="h-4 w-4" />
                    <span>방향키/WASD 이동, +/- 확대·축소, [ ] 페이지 전환</span>
                  </div>
                  {lastClick ? <span className="rounded-full border border-border bg-muted px-3 py-1">최근 클릭 {lastClick.x}, {lastClick.y}</span> : null}
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/70 shadow-soft" data-testid="answer-card">
              <CardHeader className="pb-4">
                <CardTitle className="text-base">정답 제출</CardTitle>
                <CardDescription>숫자 또는 선택지 텍스트를 그대로 입력합니다.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-3">
                  <Input
                    value={answer}
                    onChange={(event) => setAnswer(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        void applyAction({ type: 'submit_answer', text: answer })
                      }
                    }}
                    placeholder="숫자 또는 단위를 포함해 입력"
                    disabled={isLoading}
                  />
                  <Button onClick={() => void applyAction({ type: 'submit_answer', text: answer })} disabled={isLoading} className="min-w-32">
                    <Send className="mr-2 h-4 w-4" />
                    정답 제출
                  </Button>
                </div>
                {errorText ? <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">{errorText}</div> : null}
              </CardContent>
            </Card>
          </main>

          <aside className={isInspectorOpen ? 'block' : 'hidden'}>
            <Card className="sticky top-5 border-border/70 bg-card/95 shadow-soft" data-testid="inspector-panel">
              <CardHeader className="pb-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-2">
                    <Badge variant="outline" className="rounded-full px-3 py-1">
                      <Activity className="mr-1 h-3.5 w-3.5" />
                      Inspector
                    </Badge>
                    <CardTitle className="text-lg">보조 정보와 기록</CardTitle>
                    <CardDescription>기본 화면은 플레이에 집중하고, 상세 로그와 replay는 여기에서 봅니다.</CardDescription>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => setIsInspectorOpen(false)}>
                    닫기
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <Tabs value={inspectorTab} onValueChange={(value) => void openInspector(value as InspectorTab)} className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="session">세션</TabsTrigger>
                    <TabsTrigger value="log">최근 액션</TabsTrigger>
                    <TabsTrigger value="replay">리플레이</TabsTrigger>
                    <TabsTrigger value="help">도움말</TabsTrigger>
                  </TabsList>

                  <TabsContent value="session">
                    <Card className="border-0 shadow-none">
                      <CardHeader className="px-0 pb-4">
                        <CardTitle className="text-base">세션 메타데이터</CardTitle>
                      </CardHeader>
                      <CardContent className="px-0">
                        <InfoGrid items={inspectorItems} />
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="log">
                    <EventFeed
                      title="최근 액션"
                      description="가장 최근 수행된 액션을 시간 역순으로 확인합니다."
                      events={events.slice(-12).reverse()}
                      emptyText="아직 수행된 액션이 없습니다."
                      renderAction={describeAction}
                      renderDetail={describeEventDetail}
                    />
                  </TabsContent>

                  <TabsContent value="replay">
                    <div className="mb-4 flex justify-end">
                      <Button variant="outline" size="sm" onClick={() => (sessionId ? void loadReplay(sessionId) : undefined)}>
                        <RefreshCw className="mr-2 h-4 w-4" />
                        새로고침
                      </Button>
                    </div>
                    <EventFeed
                      title="리플레이"
                      description="에피소드 종료 후 replay trace를 검토합니다."
                      events={replay.slice(-12).reverse()}
                      emptyText="에피소드가 종료되면 이곳에서 리플레이를 확인할 수 있습니다."
                      renderAction={describeAction}
                      renderDetail={describeEventDetail}
                    />
                  </TabsContent>

                  <TabsContent value="help">
                    <Card className="border-0 shadow-none">
                      <CardHeader className="px-0 pb-4">
                        <CardTitle className="text-base">조작 가이드</CardTitle>
                      </CardHeader>
                      <CardContent className="px-0">
                        <ScrollArea className="h-[440px] pr-4">
                          <ul className="space-y-3 text-sm leading-7 text-muted-foreground">
                            <li>방향키 또는 WASD로 뷰포트를 이동합니다.</li>
                            <li><code>+</code> / <code>-</code> 로 확대와 축소를 합니다.</li>
                            <li><code>[</code> / <code>]</code> 로 페이지를 넘깁니다.</li>
                            <li>표를 직접 클릭하면 좌표 기반 액션이 전송되고, 최근 액션에서 대상 영역을 확인할 수 있습니다.</li>
                            <li>기본 화면은 질문과 뷰포트에 집중하고, 상세 기록과 설명은 Inspector에 모아둡니다.</li>
                          </ul>
                        </ScrollArea>
                      </CardContent>
                    </Card>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </aside>
        </div>
      </div>
    </div>
  )
}

export default App
