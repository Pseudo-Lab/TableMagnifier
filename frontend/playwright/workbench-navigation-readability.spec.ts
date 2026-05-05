import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'

import { expect, test, type Page } from '@playwright/test'

import {
  createConsoleCollector,
  dumpFailureArtifacts,
  matchedRequiredViewportStateIds,
  readDebugMetrics,
  rectBottom,
  type RequiredViewportState,
  type ViewportStateSnapshot,
} from './readability-helpers'

type RequiredNavigation = {
  required_viewport_states?: RequiredViewportState[]
}

type SessionStartTarget = {
  packId: string | null
  instanceId: string | null
  family: string | null
  requiredNavigation: RequiredNavigation
  initialSnapshot: ViewportStateSnapshot | null
}

function snapshotFromInfo(info: Record<string, unknown> | undefined, cumulativeActionTypes: string[]): ViewportStateSnapshot | null {
  if (!info) {
    return null
  }
  if (!info.active_sheet_id || !info.current_page_id || !info.viewbox) {
    return null
  }
  return {
    sheet_id: info.active_sheet_id as string,
    page_id: info.current_page_id as string,
    zoom_index: (info.zoom_index as number | undefined) ?? 0,
    viewbox: info.viewbox as ViewportStateSnapshot['viewbox'],
    cumulative_action_types: [...cumulativeActionTypes],
  }
}

function filterConsoleMessages(messages: string[]) {
  return messages.filter((message) => !message.toLowerCase().includes('favicon'))
}

function parsePageLabel(text: string) {
  const match = text.match(/(.+?)\s*·\s*(\d+)\/(\d+)/)
  if (!match) {
    return null
  }
  return {
    sheet: match[1].trim(),
    current: Number(match[2]),
    total: Number(match[3]),
  }
}

async function startTargetSession(page: Page) {
  const targetPackId = process.env.PLAYWRIGHT_TARGET_PACK_ID
  const targetInstanceId = process.env.PLAYWRIGHT_TARGET_INSTANCE_ID
  const targetFamily = process.env.PLAYWRIGHT_TARGET_FAMILY
  const targetLevel = process.env.PLAYWRIGHT_TARGET_LEVEL
  const targetSeed = process.env.PLAYWRIGHT_TARGET_SEED

  if (targetInstanceId) {
    const packSelect = page.locator('[data-testid="instance-pack-select"]')
    const instanceSelect = page.locator('[data-testid="instance-select"]')
    let expectedInstanceLabel: string | null = null

    if (targetPackId) {
      await packSelect.selectOption(targetPackId)
      await expect.poll(async () => packSelect.inputValue()).toBe(targetPackId)
      await expect
        .poll(async () => {
          return await instanceSelect.locator('option').evaluateAll((options) =>
            options.map((option) => (option as HTMLOptionElement).value),
          )
        })
        .toContain(targetInstanceId)
    }

    await instanceSelect.selectOption(targetInstanceId)
    await expect.poll(async () => instanceSelect.inputValue()).toBe(targetInstanceId)
    expectedInstanceLabel = (await instanceSelect.locator(`option[value="${targetInstanceId}"]`).textContent())?.trim() ?? null
    const sessionResponsePromise = page.waitForResponse((response) => response.url().includes('/api/sessions') && response.request().method() === 'POST')
    await page.locator('[data-testid="start-instance-button"]').click()
    const sessionPayload = await (await sessionResponsePromise).json()
    await expect(page.getByText('세션을 불러오는 중입니다.')).not.toBeVisible()
    if (expectedInstanceLabel) {
      await expect
        .poll(async () => ((await page.locator('[data-testid="question-card"]').textContent()) ?? '').replace(/\s+/g, ' ').trim())
        .toContain(expectedInstanceLabel)
    }
    return {
      packId: targetPackId ?? null,
      instanceId: targetInstanceId,
      family: null,
      requiredNavigation: (sessionPayload.info?.required_navigation ?? {}) as RequiredNavigation,
      initialSnapshot: snapshotFromInfo(sessionPayload.info, []),
    }
  }

  if (!targetFamily && !targetLevel && !targetSeed) {
    return {
      packId: null,
      instanceId: null,
      family: null,
      requiredNavigation: {},
      initialSnapshot: null,
    }
  }

  if (targetFamily) {
    await page.locator('[data-testid="family-select"]').selectOption(targetFamily)
  }
  if (targetLevel) {
    await page.locator('[data-testid="level-select"]').selectOption(targetLevel)
  }
  if (targetSeed) {
    await page.locator('[data-testid="seed-input"]').fill(targetSeed)
  }

  const sessionResponsePromise = page.waitForResponse((response) => response.url().includes('/api/sessions') && response.request().method() === 'POST')
  await page.locator('[data-testid="start-session-button"]').click()
  const sessionPayload = await (await sessionResponsePromise).json()
  await expect(page.getByText('세션을 불러오는 중입니다.')).not.toBeVisible()
  return {
    packId: null,
    instanceId: null,
    family: targetFamily ?? null,
    requiredNavigation: (sessionPayload.info?.required_navigation ?? {}) as RequiredNavigation,
    initialSnapshot: snapshotFromInfo(sessionPayload.info, []),
  }
}

function snapshotFromStepPayload(payload: Record<string, unknown>, cumulativeActionTypes: string[]): ViewportStateSnapshot | null {
  const info = payload.info as { last_event?: { after?: Record<string, unknown> } } | undefined
  const after = info?.last_event?.after
  if (!after) {
    return null
  }
  return {
    sheet_id: (after.sheet_id as string | undefined) ?? null,
    page_id: (after.page_id as string | undefined) ?? null,
    zoom_index: (after.zoom_index as number | undefined) ?? null,
    viewbox: (after.viewbox as ViewportStateSnapshot['viewbox']) ?? null,
    cumulative_action_types: [...cumulativeActionTypes],
  }
}

async function clickActionAndCollect(
  page: Page,
  actionType: string,
  click: () => Promise<unknown>,
  snapshots: ViewportStateSnapshot[],
  cumulativeActionTypes: string[],
) {
  const responsePromise = page.waitForResponse((response) => response.url().includes('/api/sessions/') && response.url().includes('/actions') && response.request().method() === 'POST')
  await click()
  const payload = (await (await responsePromise).json()) as Record<string, unknown>
  cumulativeActionTypes.push(actionType)
  const snapshot = snapshotFromStepPayload(payload, cumulativeActionTypes)
  if (snapshot) {
    snapshots.push(snapshot)
  }
}

async function performRequiredViewportActions(
  page: Page,
  requiredState: RequiredViewportState,
  snapshots: ViewportStateSnapshot[],
  cumulativeActionTypes: string[],
) {
  const actionLocators: Record<string, ReturnType<Page['locator']>> = {
    zoom_in: page.getByRole('button', { name: /확대/ }),
    zoom_out: page.getByRole('button', { name: /축소/ }),
    pan_up: page.getByRole('button', { name: '↑' }),
    pan_down: page.getByRole('button', { name: '↓' }),
    pan_left: page.getByRole('button', { name: '←' }),
    pan_right: page.getByRole('button', { name: '→' }),
  }
  for (const actionType of requiredState.required_action_types ?? []) {
    const locator = actionLocators[actionType]
    if (!locator) {
      continue
    }
    await clickActionAndCollect(page, actionType, () => locator.click(), snapshots, cumulativeActionTypes)
    await expect(page.locator('[data-testid="viewer-surface"] canvas')).toBeVisible()
  }
}

async function openScopeNoteIfPresent(
  page: Page,
  viewerSurface: ReturnType<Page['locator']>,
  viewerCanvas: ReturnType<Page['locator']>,
) {
  let noteMarker: Awaited<ReturnType<typeof readDebugMetrics>>['regions'][number] | null = null
  await expect
    .poll(async () => {
      const metrics = await readDebugMetrics(page)
      noteMarker = metrics?.regions.find((region) => region.role === 'note_marker') ?? null
      return noteMarker !== null
    })
    .toBeTruthy()

  if (!noteMarker) {
    return null
  }
  const [surfaceBox, canvasBox] = await Promise.all([viewerSurface.boundingBox(), viewerCanvas.boundingBox()])
  if (!surfaceBox || !canvasBox) {
    return null
  }
  const clickX = canvasBox.x - surfaceBox.x + noteMarker.rect.x + noteMarker.rect.width / 2
  const clickY = canvasBox.y - surfaceBox.y + noteMarker.rect.y + noteMarker.rect.height / 2
  await viewerSurface.click({ position: { x: clickX, y: clickY } })
  await expect
    .poll(async () => (await readDebugMetrics(page))?.overlayNote?.id ?? null)
    .toBeTruthy()
  const openedMetrics = await readDebugMetrics(page)
  return openedMetrics?.overlayNote?.id ?? noteMarker.label
}

test('workbench navigation readability covers every available page', async ({ page }, testInfo) => {
  const root = page.locator('#root')
  const viewerCanvas = page.locator('[data-testid="viewer-surface"] canvas')
  const viewerSurface = page.locator('[data-testid="viewer-surface"]')
  const questionCard = page.locator('[data-testid="question-card"]')
  const viewerPanel = page.locator('[data-testid="viewer-panel"]')
  const answerCard = page.locator('[data-testid="answer-card"]')
  const pageLabel = page.locator('[data-testid="page-label"]')
  const nextPageButton = page.locator('[data-testid="next-page-button"]')
  const prevPageButton = page.locator('[data-testid="prev-page-button"]')
  const sheetButtons = page.locator('[data-testid="sheet-tab-button"]')
  const consoleMessages = createConsoleCollector(page)
  const visitedPages = new Set<string>()
  const multiPageSheets = new Set<string>()
  const openedNotes = new Set<string>()
  const viewportSnapshots: ViewportStateSnapshot[] = []
  const cumulativeActionTypes: string[] = []
  let selectedTarget: SessionStartTarget | undefined

  try {
    await page.goto('/', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('한국어 Visual TableQA Workbench')).toBeVisible()
    await viewerCanvas.waitFor({ state: 'visible', timeout: 20_000 })
    await expect(page.getByText('세션을 불러오는 중입니다.')).not.toBeVisible()
    selectedTarget = await startTargetSession(page)
    if (selectedTarget.initialSnapshot) {
      viewportSnapshots.push(selectedTarget.initialSnapshot)
    }
    await viewerCanvas.waitFor({ state: 'visible', timeout: 20_000 })

    const [questionBox, viewerBox, answerBox] = await Promise.all([
      questionCard.boundingBox(),
      viewerPanel.boundingBox(),
      answerCard.boundingBox(),
    ])
    expect(questionBox).not.toBeNull()
    expect(viewerBox).not.toBeNull()
    expect(answerBox).not.toBeNull()
    if (!questionBox || !viewerBox || !answerBox) {
      return
    }

    expect(rectBottom(questionBox)).toBeLessThanOrEqual(viewerBox.y + 4)
    expect(rectBottom(viewerBox)).toBeLessThanOrEqual(answerBox.y + 4)

    const sheetNames = (await sheetButtons.evaluateAll((buttons) =>
      buttons
        .map((button) => button.getAttribute('data-sheet-name') ?? button.textContent ?? '')
        .map((value) => value.trim())
        .filter(Boolean),
    )) as string[]
    expect(sheetNames.length).toBeGreaterThan(0)

    for (const sheetName of sheetNames) {
      const button = page.locator(`[data-testid="sheet-tab-button"][data-sheet-name="${sheetName}"]`)
      if (!sheetName) {
        continue
      }
      let selected = false
      for (let attempt = 0; attempt < 3; attempt += 1) {
        const currentSheet = parsePageLabel((await pageLabel.textContent()) ?? '')?.sheet ?? ''
        if (currentSheet === sheetName) {
          selected = true
          break
        }
        if (!(await button.isDisabled())) {
          await clickActionAndCollect(page, 'select_sheet', () => button.click(), viewportSnapshots, cumulativeActionTypes)
          await expect(viewerCanvas).toBeVisible()
        }
        try {
          await expect
            .poll(async () => parsePageLabel((await pageLabel.textContent()) ?? '')?.sheet ?? '', { timeout: 4_000 })
            .toBe(sheetName)
          selected = true
          break
        } catch {
          // Retry flaky sheet-tab clicks a few times before failing the traversal.
        }
      }
      expect(selected).toBeTruthy()
      await expect(button).toBeDisabled()

      let pageInfo = parsePageLabel((await pageLabel.textContent()) ?? '')
      expect(pageInfo).not.toBeNull()
      if (!pageInfo) {
        continue
      }

      while (pageInfo.current > 1) {
        await clickActionAndCollect(page, 'prev_page', () => prevPageButton.click(), viewportSnapshots, cumulativeActionTypes)
        await expect
          .poll(async () => parsePageLabel((await pageLabel.textContent()) ?? '')?.current ?? 0)
          .toBe(pageInfo.current - 1)
        pageInfo = parsePageLabel((await pageLabel.textContent()) ?? '')
        expect(pageInfo).not.toBeNull()
        if (!pageInfo) {
          break
        }
      }
      if (!pageInfo) {
        continue
      }

      for (let pageNumber = pageInfo.current; pageNumber <= pageInfo.total; pageNumber += 1) {
        const currentInfo = parsePageLabel((await pageLabel.textContent()) ?? '')
        expect(currentInfo).not.toBeNull()
        if (!currentInfo) {
          break
        }
        expect(currentInfo.current).toBe(pageNumber)
        visitedPages.add(`${sheetName}:${pageNumber}/${currentInfo.total}`)
        if (currentInfo.total > 1) {
          multiPageSheets.add(sheetName)
        }
        await expect(viewerCanvas).toBeVisible()

        const metrics = await readDebugMetrics(page)
        const hasNoteMarker = (metrics?.regions ?? []).some((region) => region.role === 'note_marker')
        if (hasNoteMarker) {
          const responsePromise = page.waitForResponse((response) => response.url().includes('/api/sessions/') && response.url().includes('/actions') && response.request().method() === 'POST')
          const openedNote = await openScopeNoteIfPresent(page, viewerSurface, viewerCanvas)
          const payload = (await (await responsePromise).json()) as Record<string, unknown>
          cumulativeActionTypes.push('click_region')
          const snapshot = snapshotFromStepPayload(payload, cumulativeActionTypes)
          if (snapshot) {
            viewportSnapshots.push(snapshot)
          }
          expect(openedNote).toBeTruthy()
          openedNotes.add(openedNote as string)
        }

        const currentSnapshot = viewportSnapshots.at(-1)
        for (const requiredState of selectedTarget?.requiredNavigation.required_viewport_states ?? []) {
          if (currentSnapshot?.sheet_id !== requiredState.sheet_id || currentSnapshot?.page_id !== requiredState.page_id) {
            continue
          }
          await performRequiredViewportActions(page, requiredState, viewportSnapshots, cumulativeActionTypes)
        }

        if (pageNumber < currentInfo.total) {
          await clickActionAndCollect(page, 'next_page', () => nextPageButton.click(), viewportSnapshots, cumulativeActionTypes)
          await expect
            .poll(async () => parsePageLabel((await pageLabel.textContent()) ?? '')?.current ?? 0)
            .toBe(pageNumber + 1)
        }
      }
    }

    const consoleErrors = filterConsoleMessages(consoleMessages)
    expect(consoleErrors).toEqual([])
    expect(visitedPages.size).toBeGreaterThan(0)
    const visitedViewportStates = matchedRequiredViewportStateIds(
      selectedTarget?.requiredNavigation.required_viewport_states ?? [],
      viewportSnapshots,
    )

    const summaryPath = process.env.PLAYWRIGHT_WORKBENCH_SUMMARY_PATH
    if (summaryPath) {
      mkdirSync(path.dirname(summaryPath), { recursive: true })
      writeFileSync(
        summaryPath,
        JSON.stringify(
          {
            pack_id: selectedTarget?.packId ?? null,
            instance_id: selectedTarget?.instanceId ?? null,
            family: selectedTarget?.family ?? null,
            visited_pages: Array.from(visitedPages.values()),
            multi_page_sheets: Array.from(multiPageSheets.values()),
            opened_notes: Array.from(openedNotes.values()),
            visited_viewport_states: visitedViewportStates,
            sheet_count: sheetNames.length,
          },
          null,
          2,
        ),
        'utf-8',
      )
    }
  } catch (error) {
    await dumpFailureArtifacts(page, testInfo, 'workbench-navigation', {
      consoleMessages,
      locator: root,
    })
    throw error
  }
})
