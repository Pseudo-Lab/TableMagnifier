import { expect, test } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

const route = process.env.PLAYWRIGHT_CAPTURE_ROUTE ?? '/'
const readySelector = process.env.PLAYWRIGHT_READY_SELECTOR ?? '.viewer-surface canvas'
const captureDir = process.env.PLAYWRIGHT_CAPTURE_DIR ?? path.resolve(process.cwd(), '../artifacts/playwright')

test('capture workbench states', async ({ page }, testInfo) => {
  const projectSuffix = testInfo.project.name.replace(/^chromium-/, '')
  await page.goto(route, { waitUntil: 'domcontentloaded' })
  await expect(page.getByText('K-VisTable-ARC Agent Workbench')).toBeVisible()
  await page.locator(readySelector).waitFor({ state: 'visible', timeout: 20_000 })
  await page.waitForTimeout(500)

  await mkdir(captureDir, { recursive: true })
  await page.screenshot({ path: path.join(captureDir, `workbench-session-${projectSuffix}.png`), fullPage: true })

  await page.getByRole('button', { name: 'Inspector 열기' }).click()
  await expect(page.getByText('보조 정보와 기록')).toBeVisible()
  await page.waitForTimeout(250)
  await page.screenshot({ path: path.join(captureDir, `workbench-inspector-${projectSuffix}.png`), fullPage: true })

  await page.getByRole('button', { name: '닫기' }).click()
  await expect(page.getByText('보조 정보와 기록')).not.toBeVisible()
  await page.waitForTimeout(250)
  await page.screenshot({ path: path.join(captureDir, `workbench-focus-${projectSuffix}.png`), fullPage: true })
})
