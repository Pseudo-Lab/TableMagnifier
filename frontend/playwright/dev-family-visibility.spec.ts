import { expect, test, type APIRequestContext } from '@playwright/test'

const ACTIVE_FAMILY = 'k_vis_table_arc'
const ACTIVE_LABEL = 'K-VisTable-ARC 파일럿'

async function defaultGeneratedRecord(request: APIRequestContext) {
  const response = await request.get('/api/benchmark-suites')
  expect(response.ok()).toBeTruthy()
  const payload = await response.json()
  const suite = payload.suites[0]
  const template = suite.templates[0]
  const record = template.records[0]
  return { suite, template, record }
}

test('dev family selector labels active generator families', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('[data-testid="viewer-surface"] canvas')).toBeVisible({ timeout: 20_000 })

  const familySelect = page.locator('[data-testid="family-select"]')
  await expect
    .poll(async () => familySelect.locator('option').evaluateAll((options) => options.map((option) => option.textContent?.trim() ?? '')))
    .toContain(`${ACTIVE_LABEL} · 우선`)

  await familySelect.selectOption(ACTIVE_FAMILY)
  await expect(page.locator('[data-testid="family-status-badge"]')).toHaveText('preferred')
})

test('generated benchmark selector starts the default canonical record', async ({ page, request }) => {
  const expected = await defaultGeneratedRecord(request)
  const sessionResponsePromise = page.waitForResponse((response) => response.url().includes('/api/sessions') && response.request().method() === 'POST')

  await page.goto('/', { waitUntil: 'domcontentloaded' })
  const sessionPayload = await (await sessionResponsePromise).json()
  await expect(page.locator('[data-testid="viewer-surface"] canvas')).toBeVisible({ timeout: 20_000 })

  await expect(page.locator('[data-testid="generated-suite-select"]')).toHaveValue(expected.suite.suite_id)
  await expect(page.locator('[data-testid="generated-template-select"]')).toHaveValue(`${expected.template.family}::${expected.template.level}::${expected.template.template_id}`)
  await expect(page.locator('[data-testid="generated-seed-slot-select"]')).toHaveValue(`${expected.record.family}::${expected.record.level}::${expected.record.template_id}::${expected.record.seed}`)
  await expect(page.locator('[data-testid="instance-select"]')).toHaveCount(0)

  expect(sessionPayload.info.template_id).toBe(expected.record.template_id)
  expect(sessionPayload.info.episode_id).toBe(expected.record.episode_id)
  await expect(page.locator('[data-testid="question-card"]')).toContainText(expected.template.family_display_name)
  await expect.poll(async () => {
    return await page.evaluate(() => {
      return (window as typeof window & { __TABLE_ENV_DEBUG__?: { elements?: unknown[] } }).__TABLE_ENV_DEBUG__?.elements?.length ?? 0
    })
  }).toBeGreaterThan(0)
})

test('generated benchmark selector launches only declared seed-slot records', async ({ page, request }) => {
  const expected = await defaultGeneratedRecord(request)
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('[data-testid="viewer-surface"] canvas')).toBeVisible({ timeout: 20_000 })

  const generatedSeedSelect = page.locator('[data-testid="generated-seed-slot-select"]')
  await expect
    .poll(async () => generatedSeedSelect.locator('option').evaluateAll((options) => options.map((option) => (option as HTMLOptionElement).value)))
    .toEqual(expected.template.records.map((record: { family: string; level: number; template_id: string; seed: number }) => `${record.family}::${record.level}::${record.template_id}::${record.seed}`))
  await expect(page.locator('[data-testid="generated-seed-input"]')).toHaveCount(0)

  const sessionResponsePromise = page.waitForResponse((response) => response.url().includes('/api/sessions') && response.request().method() === 'POST')
  await page.locator('[data-testid="start-generated-button"]').click()
  const sessionPayload = await (await sessionResponsePromise).json()
  expect(sessionPayload.info.template_id).toBe(expected.record.template_id)
  expect(sessionPayload.info.episode_id).toBe(expected.record.episode_id)
})

test('direct dev-family URL starts requested generator session', async ({ page }) => {
  await page.goto(`/?family=${ACTIVE_FAMILY}&level=1&seed=0`, { waitUntil: 'domcontentloaded' })
  await expect(page.locator('[data-testid="viewer-surface"] canvas')).toBeVisible({ timeout: 20_000 })

  await expect(page.locator('[data-testid="question-card"]')).toContainText(ACTIVE_LABEL)
  await expect(page.locator('[data-testid="family-select"]')).toHaveValue(ACTIVE_FAMILY)
  await expect(page.locator('[data-testid="level-select"]')).toHaveValue('1')
  await expect(page.locator('[data-testid="seed-input"]')).toHaveValue('0')

  const viewerSurface = page.locator('[data-testid="viewer-surface"]')
  await expect(viewerSurface).toHaveAttribute('data-active-sheet-id', 'examples')
  await expect(viewerSurface).toHaveAttribute('data-current-page-id', 'examples-p1')
  await expect(viewerSurface).toHaveAttribute('data-zoom-index', '0')
  await expect(viewerSurface).toHaveAttribute('data-viewbox', /"width"/)
})

test('invalid dev-family URL falls back to default generated benchmark startup', async ({ page, request }) => {
  const expected = await defaultGeneratedRecord(request)
  const sessionResponsePromise = page.waitForResponse((response) => response.url().includes('/api/sessions') && response.request().method() === 'POST')
  await page.goto(`/?family=${ACTIVE_FAMILY}&level=99&seed=0`, { waitUntil: 'domcontentloaded' })
  const sessionPayload = await (await sessionResponsePromise).json()
  await expect(page.locator('[data-testid="viewer-surface"] canvas')).toBeVisible({ timeout: 20_000 })

  await expect(page.locator('[data-testid="question-card"]')).not.toContainText('level=99')
  await expect(page.locator('[data-testid="family-select"]')).toHaveValue(ACTIVE_FAMILY)
  await expect(page.locator('[data-testid="instance-select"]')).toHaveCount(0)
  await expect(page.locator('[data-testid="generated-suite-select"]')).toHaveValue(expected.suite.suite_id)
  await expect(page.locator('[data-testid="generated-template-select"]')).toHaveValue(`${expected.template.family}::${expected.template.level}::${expected.template.template_id}`)
  await expect(page.locator('[data-testid="generated-seed-slot-select"]')).toHaveValue(`${expected.record.family}::${expected.record.level}::${expected.record.template_id}::${expected.record.seed}`)
  expect(sessionPayload.info.template_id).toBe(expected.record.template_id)
  expect(sessionPayload.info.episode_id).toBe(expected.record.episode_id)
})
