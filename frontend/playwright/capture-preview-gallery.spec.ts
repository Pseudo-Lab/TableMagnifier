import { readFileSync } from 'node:fs'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

import { expect, test } from '@playwright/test'

type SurfacePreview = {
  surface_id: string
  family: string
  level: string
  sheet_id: string
  page_id: string
}

type SurfaceManifest = {
  previews: SurfacePreview[]
}

const reviewDir = path.resolve(process.cwd(), process.env.PLAYWRIGHT_REVIEW_DIR ?? '../artifacts/previews_active')
const captureDir = path.resolve(process.cwd(), process.env.PLAYWRIGHT_CAPTURE_DIR ?? '../artifacts/playwright/previews_active')
const manifestPath = path.join(reviewDir, 'manifest.json')
const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8')) as SurfaceManifest

function safeName(value: string) {
  return value.replace(/[^a-zA-Z0-9._-]+/g, '_')
}

for (const preview of manifest.previews) {
  test(`capture preview surface: ${preview.surface_id}`, async ({ page }, testInfo) => {
    const projectSuffix = testInfo.project.name.replace(/^chromium-/, '')
    const canvas = page.locator('#surface-canvas')
    await page.goto(`/review.html?surface=${encodeURIComponent(preview.surface_id)}`, { waitUntil: 'domcontentloaded' })
    await expect(canvas).toBeVisible()
    await page.waitForFunction(() => {
      const canvas = document.querySelector<HTMLCanvasElement>('#surface-canvas')
      if (!canvas) {
        return false
      }
      const context = canvas.getContext('2d')
      if (!context) {
        return false
      }
      const sample = context.getImageData(0, 0, canvas.width, canvas.height).data
      return sample.some((channel, index) => index % 4 !== 3 && channel !== 255)
    })

    const familyDir = path.join(captureDir, safeName(preview.family), `level-${safeName(preview.level)}`)
    await mkdir(familyDir, { recursive: true })
    const fileName = [
      safeName(preview.surface_id),
      safeName(preview.sheet_id),
      safeName(preview.page_id),
      projectSuffix,
    ].join('__')
    await canvas.screenshot({ path: path.join(familyDir, `${fileName}.png`) })
  })
}
