import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

import { expect, type Locator, type Page, type TestInfo } from '@playwright/test'

export type Rect = {
  x: number
  y: number
  width: number
  height: number
}

export type RequiredViewportTarget = {
  target_id?: string
  kind?: string
  rect: Rect
}

export type RequiredViewportState = {
  state_id: string
  sheet_id: string
  page_id: string
  min_zoom_index?: number
  required_action_types?: string[]
  match?: 'target_center_in_viewbox' | 'viewbox_intersects_target' | string
  target_rects?: RequiredViewportTarget[]
}

export type ViewportStateSnapshot = {
  sheet_id?: string | null
  page_id?: string | null
  zoom_index?: number | null
  viewbox?: Rect | null
  cumulative_action_types?: string[]
}

export type DebugElement = {
  id: string
  type: string
  rect: Rect
  title?: string
  titleBox?: Rect | null
  subtitleBox?: Rect | null
  lineBoxes?: Rect[]
  contentRect?: Rect | null
  textBottom?: number
  overflowY?: boolean
  padding?: number
  cellOverflowCount?: number
  cellTextMetrics?: Array<{
    row: number
    col: number
    text: string
    textRect: Rect
    contentRect: Rect
    overflowX: boolean
    overflowY: boolean
  }>
}

export type DebugRegion = {
  publicId: string
  role: string
  label: string
  rect: Rect
}

export type DebugMetrics = {
  surfaceId: string | null
  canvasSize: { width: number; height: number }
  contentFrame: Rect
  pageTitleBox: Rect
  pageMetaBox: Rect
  elements: DebugElement[]
  regions: DebugRegion[]
  overlayNote?: DebugElement | null
  invalidLayout?: boolean
  layoutErrors?: Array<{
    code: string
    message: string
    elementId?: string
    cellKey?: string
    overlappingElementId?: string
  }>
  consoleErrors: string[]
}

const artifactRoot = path.resolve(process.cwd(), process.env.PLAYWRIGHT_ARTIFACT_ROOT ?? '../artifacts/playwright/readability')

export function createConsoleCollector(page: Page) {
  const messages: string[] = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      messages.push(msg.text())
    }
  })
  page.on('pageerror', (error) => {
    messages.push(String(error))
  })
  return messages
}

export async function readDebugMetrics(page: Page) {
  try {
    const metrics = await page.evaluate(() => (window as Window & { __TABLE_ENV_DEBUG__?: unknown }).__TABLE_ENV_DEBUG__)
    return metrics as DebugMetrics | null
  } catch {
    return null
  }
}

export async function expectCanvasReady(page: Page, expectedSurfaceId?: string) {
  await page.waitForFunction(
    (surfaceId) => {
      const bodyState = document.body.dataset.surfaceLoaded
      const metrics = (window as Window & { __TABLE_ENV_DEBUG__?: { surfaceId?: string | null } }).__TABLE_ENV_DEBUG__
      if (!metrics) {
        return false
      }
      if (!surfaceId) {
        return bodyState !== 'pending'
      }
      return bodyState === surfaceId && metrics.surfaceId === surfaceId
    },
    expectedSurfaceId,
    { timeout: 20_000 },
  )
}

export async function dumpFailureArtifacts(
  page: Page,
  testInfo: TestInfo,
  slug: string,
  extras: { debug?: unknown; consoleMessages?: string[]; locator?: Locator; scene?: unknown } = {},
) {
  const baseDir = path.join(artifactRoot, slug)
  await mkdir(baseDir, { recursive: true })
  try {
    await page.screenshot({ path: path.join(baseDir, 'page.png'), fullPage: true })
  } catch (error) {
    void error
  }
  if (extras.locator) {
    try {
      await extras.locator.screenshot({ path: path.join(baseDir, 'surface.png') })
    } catch (error) {
      void error
    }
  }
  if (extras.debug !== undefined) {
    await writeFile(path.join(baseDir, 'debug.json'), JSON.stringify(extras.debug, null, 2), 'utf-8')
  }
  if (extras.scene !== undefined) {
    await writeFile(path.join(baseDir, 'scene.json'), JSON.stringify(extras.scene, null, 2), 'utf-8')
  }
  if (extras.consoleMessages) {
    await writeFile(path.join(baseDir, 'console.log'), extras.consoleMessages.join('\n'), 'utf-8')
  }
  testInfo.attachments.push({
    name: `${slug}-artifacts`,
    contentType: 'text/plain',
    body: Buffer.from(baseDir, 'utf-8'),
  })
}

export function rectBottom(rect: Rect) {
  return rect.y + rect.height
}

export function rectRight(rect: Rect) {
  return rect.x + rect.width
}

export function viewportTargetMatches(viewbox: Rect, targetRect: Rect, match: string) {
  if (match === 'viewbox_intersects_target') {
    return overlapAmount(viewbox, targetRect).overlapX * overlapAmount(viewbox, targetRect).overlapY > 0
  }
  if (match === 'target_center_in_viewbox') {
    const centerX = targetRect.x + targetRect.width / 2
    const centerY = targetRect.y + targetRect.height / 2
    return centerX >= viewbox.x && centerX <= rectRight(viewbox) && centerY >= viewbox.y && centerY <= rectBottom(viewbox)
  }
  return false
}

export function viewportStateMatches(requiredState: RequiredViewportState, snapshot: ViewportStateSnapshot) {
  if (snapshot.sheet_id !== requiredState.sheet_id) {
    return false
  }
  if (snapshot.page_id !== requiredState.page_id) {
    return false
  }
  if ((snapshot.zoom_index ?? 0) < (requiredState.min_zoom_index ?? 0)) {
    return false
  }
  const cumulativeActions = new Set(snapshot.cumulative_action_types ?? [])
  for (const actionType of requiredState.required_action_types ?? []) {
    if (!cumulativeActions.has(actionType)) {
      return false
    }
  }
  if (!snapshot.viewbox) {
    return false
  }
  const matchMode = requiredState.match ?? 'target_center_in_viewbox'
  return (requiredState.target_rects ?? []).every((target) => viewportTargetMatches(snapshot.viewbox as Rect, target.rect, matchMode))
}

export function matchedRequiredViewportStateIds(
  requiredStates: RequiredViewportState[],
  snapshots: ViewportStateSnapshot[],
) {
  const matched: string[] = []
  const matchedSet = new Set<string>()
  for (const snapshot of snapshots) {
    for (const requiredState of requiredStates) {
      if (matchedSet.has(requiredState.state_id)) {
        continue
      }
      if (viewportStateMatches(requiredState, snapshot)) {
        matchedSet.add(requiredState.state_id)
        matched.push(requiredState.state_id)
      }
    }
  }
  return matched
}

export function overlapAmount(a: Rect, b: Rect) {
  const overlapX = Math.max(0, Math.min(rectRight(a), rectRight(b)) - Math.max(a.x, b.x))
  const overlapY = Math.max(0, Math.min(rectBottom(a), rectBottom(b)) - Math.max(a.y, b.y))
  return { overlapX, overlapY }
}

export function assertRectInside(inner: Rect, outer: Rect, tolerance = 0) {
  expect(inner.x).toBeGreaterThanOrEqual(outer.x - tolerance)
  expect(inner.y).toBeGreaterThanOrEqual(outer.y - tolerance)
  expect(rectRight(inner)).toBeLessThanOrEqual(rectRight(outer) + tolerance)
  expect(rectBottom(inner)).toBeLessThanOrEqual(rectBottom(outer) + tolerance)
}

export async function computeCanvasStats(page: Page, selector: string) {
  return page.locator(selector).evaluate((node) => {
    const canvas = node as HTMLCanvasElement
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      return { uniqueColors: 0, nonBackgroundRatio: 0 }
    }
    const { width, height } = canvas
    const { data } = ctx.getImageData(0, 0, width, height)
    const sampleStep = 8
    const background = [data[0], data[1], data[2]]
    let sampled = 0
    let nonBackground = 0
    const colors = new Set<string>()
    for (let y = 0; y < height; y += sampleStep) {
      for (let x = 0; x < width; x += sampleStep) {
        const offset = (y * width + x) * 4
        const r = data[offset]
        const g = data[offset + 1]
        const b = data[offset + 2]
        colors.add(`${r},${g},${b}`)
        sampled += 1
        if (Math.abs(r - background[0]) + Math.abs(g - background[1]) + Math.abs(b - background[2]) > 30) {
          nonBackground += 1
        }
      }
    }
    return {
      uniqueColors: colors.size,
      nonBackgroundRatio: sampled === 0 ? 0 : nonBackground / sampled,
    }
  })
}
