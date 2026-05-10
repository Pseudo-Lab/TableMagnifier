import { readFileSync } from 'node:fs'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

import { expect, test } from '@playwright/test'

type AgentObservationSurface = {
  surface_id: string
  family: string
  level: number
  template_id: string
  seed: number
  sheet_id: string
  page_id: string
}

type AgentObservationManifest = {
  surfaces: AgentObservationSurface[]
}

const reviewDir = path.resolve(process.cwd(), process.env.PLAYWRIGHT_REVIEW_DIR ?? '../artifacts/agent_observations_active')
const captureDir = path.resolve(process.cwd(), process.env.PLAYWRIGHT_CAPTURE_DIR ?? '../artifacts/playwright/agent_observations_active')
const manifestPath = path.join(reviewDir, 'manifest.json')
const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8')) as AgentObservationManifest

function safeName(value: string | number) {
  return String(value).replace(/[^a-zA-Z0-9._-]+/g, '_')
}

for (const surface of manifest.surfaces) {
  test(`capture agent observation: ${surface.surface_id}`, async ({ page }, testInfo) => {
    const projectSuffix = testInfo.project.name.replace(/^chromium-/, '')
    const image = page.locator('#agent-observation')
    await page.goto(`/review.html?surface=${encodeURIComponent(surface.surface_id)}`, { waitUntil: 'domcontentloaded' })
    await expect(image).toBeVisible()
    await page.waitForFunction(
      (surfaceId) => {
        const image = document.querySelector<HTMLImageElement>('#agent-observation')
        return document.body.dataset.surfaceLoaded === surfaceId && image?.complete && image.naturalWidth > 0
      },
      surface.surface_id,
      { timeout: 20_000 },
    )

    const outputDir = path.join(
      captureDir,
      safeName(surface.family),
      `level-${safeName(surface.level)}`,
      safeName(surface.template_id),
      `seed-${safeName(surface.seed)}`,
    )
    await mkdir(outputDir, { recursive: true })
    const fileName = [safeName(surface.surface_id), safeName(surface.sheet_id), safeName(surface.page_id), projectSuffix].join('__')
    await image.screenshot({ path: path.join(outputDir, `${fileName}.png`) })
  })
}
