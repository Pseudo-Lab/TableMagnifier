import { readFileSync } from 'node:fs'
import path from 'node:path'

import { expect, test } from '@playwright/test'

import {
  assertRectInside,
  computeCanvasStats,
  createConsoleCollector,
  dumpFailureArtifacts,
  expectCanvasReady,
  overlapAmount,
  readDebugMetrics,
  rectBottom,
} from './readability-helpers'

type SurfacePreview = {
  surface_id: string
  family: string
  family_label: string
  level: string
  kind: string
  sheet: string
  sheet_id: string
  page: string
  page_id: string
  png: string
  scene: string
}

type SurfaceManifest = {
  seed: number
  previews: SurfacePreview[]
}

const reviewDir = path.resolve(process.cwd(), process.env.PLAYWRIGHT_REVIEW_DIR ?? '../artifacts/previews_readability_gate')
const manifestPath = path.join(reviewDir, 'manifest.json')
const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8')) as SurfaceManifest

function readScene(preview: SurfacePreview) {
  return JSON.parse(readFileSync(path.join(reviewDir, preview.scene), 'utf-8')) as Record<string, unknown>
}

function allowedConsoleMessages(messages: string[]) {
  return messages.filter((message) => !message.toLowerCase().includes('favicon'))
}

function assertCommonMetrics(metrics: NonNullable<Awaited<ReturnType<typeof readDebugMetrics>>>) {
  expect(metrics.canvasSize.width).toBe(1120)
  expect(metrics.canvasSize.height).toBe(780)
  expect(metrics.invalidLayout).toBeFalsy()
  expect(metrics.layoutErrors ?? []).toEqual([])
  assertRectInside(metrics.pageTitleBox, metrics.contentFrame, 0)
  assertRectInside(metrics.pageMetaBox, metrics.contentFrame, 0)
  for (const element of metrics.elements) {
    assertRectInside(element.rect, metrics.contentFrame, 0)
    if (element.titleBox) {
      assertRectInside(element.titleBox, metrics.contentFrame, 0)
    }
    if (element.subtitleBox) {
      assertRectInside(element.subtitleBox, metrics.contentFrame, 0)
    }
    expect(element.cellOverflowCount ?? 0).toBe(0)
  }
  for (const region of metrics.regions) {
    assertRectInside(region.rect, metrics.contentFrame, 0)
  }
  for (let i = 0; i < metrics.elements.length; i += 1) {
    for (let j = i + 1; j < metrics.elements.length; j += 1) {
      const overlap = overlapAmount(metrics.elements[i].rect, metrics.elements[j].rect)
      expect(overlap.overlapX > 0.5 && overlap.overlapY > 0.5).toBeFalsy()
    }
  }
}

function assertOverviewMetrics(metrics: NonNullable<Awaited<ReturnType<typeof readDebugMetrics>>>) {
  const firstElement = metrics.elements[0]
  expect(firstElement).toBeTruthy()
  const gapFromMeta = firstElement.rect.y - rectBottom(metrics.pageMetaBox)
  expect(gapFromMeta).toBeGreaterThanOrEqual(12)
  expect(gapFromMeta).toBeLessThanOrEqual(56)

  const firstTable = metrics.elements.find((element) => element.type === 'table')
  expect(firstTable).toBeTruthy()
  if (!firstTable || !firstTable.titleBox) {
    return
  }
  const headingBoxes = [firstTable.titleBox, firstTable.subtitleBox].filter((box): box is NonNullable<typeof box> => Boolean(box))
  const headingTop = Math.min(...headingBoxes.map((box) => box.y))
  const precedingElements = metrics.elements.filter(
    (element) => element.type !== 'table' && rectBottom(element.rect) <= firstTable.rect.y + 0.5,
  )
  for (const element of precedingElements) {
    for (const headingBox of headingBoxes) {
      const overlap = overlapAmount(element.rect, headingBox)
      expect(overlap.overlapX > 0.5 && overlap.overlapY > 0.5).toBeFalsy()
      if (overlap.overlapX > 0.5) {
        const headingGap = headingTop - rectBottom(element.rect)
        expect(headingGap).toBeGreaterThanOrEqual(8)
      }
    }
  }
  if (firstTable.subtitleBox) {
    expect(rectBottom(firstTable.titleBox) + 4).toBeLessThanOrEqual(firstTable.subtitleBox.y + 0.5)
    expect(rectBottom(firstTable.subtitleBox) + 8).toBeLessThanOrEqual(firstTable.rect.y + 0.5)
  } else {
    expect(rectBottom(firstTable.titleBox) + 8).toBeLessThanOrEqual(firstTable.rect.y + 0.5)
  }
  expect(rectBottom(firstTable.rect)).toBeLessThanOrEqual(rectBottom(metrics.contentFrame) + 0.5)
}

function assertNotesMetrics(metrics: NonNullable<Awaited<ReturnType<typeof readDebugMetrics>>>) {
  const textBlocks = metrics.elements.filter((element) => element.type === 'text_block')
  expect(textBlocks.length).toBeGreaterThan(0)
  for (const block of textBlocks) {
    expect(block.padding).toBeGreaterThanOrEqual(18)
    expect(block.overflowY).toBeFalsy()
  }
  if (textBlocks.length > 1) {
    const sorted = [...textBlocks].sort((a, b) => a.rect.y - b.rect.y)
    for (let index = 1; index < sorted.length; index += 1) {
      expect(sorted[index].rect.y - rectBottom(sorted[index - 1].rect)).toBeGreaterThanOrEqual(20)
    }
  }
}

function assertNoteOverlayMetrics(metrics: NonNullable<Awaited<ReturnType<typeof readDebugMetrics>>>) {
  expect(metrics.overlayNote).toBeTruthy()
  if (!metrics.overlayNote) {
    return
  }
  assertRectInside(metrics.overlayNote.rect, metrics.contentFrame, 0)
  expect(metrics.overlayNote.padding).toBeGreaterThanOrEqual(18)
  expect(metrics.overlayNote.overflowY).toBeFalsy()
}

function assertExceptionMetrics(metrics: NonNullable<Awaited<ReturnType<typeof readDebugMetrics>>>) {
  const exceptionElements = metrics.elements.filter((element) => element.type === 'table' || element.type === 'text_block')
  expect(exceptionElements.length).toBeGreaterThan(0)

  for (const element of exceptionElements) {
    expect(element.overflowY).toBeFalsy()
  }

  const firstElement = exceptionElements[0]
  const gapFromMeta = firstElement.rect.y - rectBottom(metrics.pageMetaBox)
  expect(gapFromMeta).toBeGreaterThanOrEqual(12)
  expect(gapFromMeta).toBeLessThanOrEqual(64)

  if (exceptionElements.length > 1) {
    const sorted = [...exceptionElements].sort((a, b) => (a.rect.y === b.rect.y ? a.rect.x - b.rect.x : a.rect.y - b.rect.y))
    for (let index = 1; index < sorted.length; index += 1) {
      const gap = sorted[index].rect.y - rectBottom(sorted[index - 1].rect)
      expect(gap).toBeGreaterThanOrEqual(12)
      expect(gap).toBeLessThanOrEqual(72)
    }
  }
}

function assertQueryMetrics(metrics: NonNullable<Awaited<ReturnType<typeof readDebugMetrics>>>) {
  const answerRegions = metrics.regions.filter((region) => region.role === 'answer_choice')
  expect(answerRegions).toHaveLength(4)
  const choiceElements = metrics.elements.filter((element) => element.title?.startsWith('선택지 '))
  expect(choiceElements).toHaveLength(4)
  for (const element of choiceElements) {
    expect(element.overflowY).toBeFalsy()
  }

  const sorted = [...answerRegions].sort((a, b) => (a.rect.y === b.rect.y ? a.rect.x - b.rect.x : a.rect.y - b.rect.y))
  const firstRow = sorted.slice(0, 2).sort((a, b) => a.rect.x - b.rect.x)
  const secondRow = sorted.slice(2, 4).sort((a, b) => a.rect.x - b.rect.x)
  const sortedChoiceElements = [...choiceElements].sort((a, b) => (a.rect.y === b.rect.y ? a.rect.x - b.rect.x : a.rect.y - b.rect.y))
  const firstChoiceRow = sortedChoiceElements.slice(0, 2)
  const secondChoiceRow = sortedChoiceElements.slice(2, 4)

  expect(Math.abs(firstRow[0].rect.y - firstRow[1].rect.y)).toBeLessThanOrEqual(4)
  expect(Math.abs(secondRow[0].rect.y - secondRow[1].rect.y)).toBeLessThanOrEqual(4)
  expect(Math.abs(firstRow[0].rect.x - secondRow[0].rect.x)).toBeLessThanOrEqual(4)
  expect(Math.abs(firstRow[1].rect.x - secondRow[1].rect.x)).toBeLessThanOrEqual(4)
  expect(Math.abs(firstRow[0].rect.height - firstRow[1].rect.height)).toBeLessThanOrEqual(4)
  expect(Math.abs(secondRow[0].rect.height - secondRow[1].rect.height)).toBeLessThanOrEqual(4)

  const columnGap = firstRow[1].rect.x - (firstRow[0].rect.x + firstRow[0].rect.width)
  const rowGap = secondRow[0].rect.y - (firstRow[0].rect.y + firstRow[0].rect.height)
  expect(columnGap).toBeGreaterThanOrEqual(20)
  expect(columnGap).toBeLessThanOrEqual(60)
  expect(rowGap).toBeGreaterThanOrEqual(12)
  expect(rowGap).toBeLessThanOrEqual(64)

  const bottomMargin = rectBottom(metrics.contentFrame) - Math.max(...answerRegions.map((region) => rectBottom(region.rect)))
  expect(bottomMargin).toBeGreaterThanOrEqual(16)

  const firstChoiceRowBottom = Math.max(...firstChoiceRow.map((element) => rectBottom(element.rect)))
  for (const lowerChoice of secondChoiceRow) {
    expect(lowerChoice.titleBox).toBeTruthy()
    if (lowerChoice.titleBox) {
      expect(lowerChoice.titleBox.y - firstChoiceRowBottom).toBeGreaterThanOrEqual(8)
    }
  }
}

function assertQueryHeaderMetrics(metrics: NonNullable<Awaited<ReturnType<typeof readDebugMetrics>>>) {
  const headerBlocks = metrics.elements.filter((element) => element.id === 'query-target' || element.id === 'query-guidance')
  if (headerBlocks.length === 0) {
    return
  }

  expect(headerBlocks).toHaveLength(2)
  for (const block of headerBlocks) {
    expect(block.overflowY).toBeFalsy()
  }

  const answerRegions = metrics.regions.filter((region) => region.role === 'answer_choice')
  expect(answerRegions.length).toBeGreaterThan(0)
  const firstAnswerTop = Math.min(...answerRegions.map((region) => region.rect.y))
  const sorted = [...headerBlocks].sort((a, b) => (a.rect.y === b.rect.y ? a.rect.x - b.rect.x : a.rect.y - b.rect.y))
  const sameRow = Math.abs(sorted[0].rect.y - sorted[1].rect.y) <= 1
  const headerTopGap = sorted[0].rect.y - rectBottom(metrics.pageMetaBox)
  const headerBottom = Math.max(...headerBlocks.map((block) => rectBottom(block.rect)))
  const followingElements = metrics.elements.filter(
    (element) =>
      element.id !== 'query-target' &&
      element.id !== 'query-guidance' &&
      element.rect.y >= headerBottom - 1,
  )
  const firstContentTop =
    followingElements.length > 0
      ? Math.min(firstAnswerTop, ...followingElements.map((element) => element.rect.y))
      : firstAnswerTop
  const contentGap = firstContentTop - headerBottom

  expect(headerTopGap).toBeGreaterThanOrEqual(8)
  expect(headerTopGap).toBeLessThanOrEqual(24)
  expect(contentGap).toBeGreaterThanOrEqual(18)
  expect(contentGap).toBeLessThanOrEqual(40)

  if (sameRow) {
    const horizontalGap = sorted[1].rect.x - (sorted[0].rect.x + sorted[0].rect.width)
    expect(horizontalGap).toBeGreaterThanOrEqual(16)
    expect(horizontalGap).toBeLessThanOrEqual(40)
    for (const block of sorted) {
      expect(block.rect.width).toBeGreaterThanOrEqual(460)
      expect(block.rect.width).toBeLessThanOrEqual(520)
      expect(block.rect.height).toBeLessThanOrEqual(92)
    }
  } else {
    expect(sorted[0].rect.width).toBeGreaterThanOrEqual(980)
    expect(sorted[1].rect.width).toBeGreaterThanOrEqual(980)
    const verticalGap = sorted[1].rect.y - rectBottom(sorted[0].rect)
    expect(verticalGap).toBeGreaterThanOrEqual(16)
    expect(verticalGap).toBeLessThanOrEqual(32)
  }
}

for (const preview of manifest.previews) {
  test(`surface readability: ${preview.surface_id}`, async ({ page }, testInfo) => {
    const canvasLocator = page.locator('#surface-canvas')
    const consoleMessages = createConsoleCollector(page)
    const scene = readScene(preview)

    try {
      await page.goto(`/review.html?surface=${encodeURIComponent(preview.surface_id)}`, { waitUntil: 'domcontentloaded' })
      await expectCanvasReady(page, preview.surface_id)
      await expect(canvasLocator).toBeVisible()

      const metrics = await readDebugMetrics(page)
      expect(metrics).not.toBeNull()
      if (!metrics) {
        return
      }

      const consoleErrors = allowedConsoleMessages([...consoleMessages, ...metrics.consoleErrors])
      expect(consoleErrors).toEqual([])
      assertCommonMetrics(metrics)

      const stats = await computeCanvasStats(page, '#surface-canvas')
      expect(stats.uniqueColors).toBeGreaterThan(25)
      expect(stats.nonBackgroundRatio).toBeGreaterThan(0.01)

      if (preview.kind === 'overview') {
        assertOverviewMetrics(metrics)
      } else if (preview.kind === 'notes') {
        assertNotesMetrics(metrics)
      } else if (preview.kind === 'exception') {
        assertExceptionMetrics(metrics)
      } else if (preview.kind === 'note_overlay') {
        assertNoteOverlayMetrics(metrics)
      } else if (preview.kind === 'query') {
        assertQueryHeaderMetrics(metrics)
        assertQueryMetrics(metrics)
      }

      await page.goto(`/review.html?surface=${encodeURIComponent(preview.surface_id)}&debug=1`, { waitUntil: 'domcontentloaded' })
      await expectCanvasReady(page, preview.surface_id)
      await expect(canvasLocator).toBeVisible()
    } catch (error) {
      await dumpFailureArtifacts(page, testInfo, preview.surface_id, {
        debug: await readDebugMetrics(page),
        consoleMessages,
        locator: canvasLocator,
        scene,
      })
      throw error
    }
  })
}
