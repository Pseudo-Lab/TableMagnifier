import { expect, test } from '@playwright/test'

const EXCEL_FAMILY = 'excel_viewport_sheet_navigation'
const EXCEL_LABEL = '스프레드시트 뷰포트 탐색'

test('dev family selector labels active generator families', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('[data-testid="viewer-surface"] canvas')).toBeVisible({ timeout: 20_000 })

  const familySelect = page.locator('[data-testid="family-select"]')
  await expect
    .poll(async () => familySelect.locator('option').evaluateAll((options) => options.map((option) => option.textContent?.trim() ?? '')))
    .toContain(`${EXCEL_LABEL} · active`)

  await familySelect.selectOption(EXCEL_FAMILY)
  await expect(page.locator('[data-testid="family-status-badge"]')).toHaveText('active')
})

test('direct dev-family URL starts requested generator session', async ({ page }) => {
  await page.goto(`/?family=${EXCEL_FAMILY}&level=1&seed=0`, { waitUntil: 'domcontentloaded' })
  await expect(page.locator('[data-testid="viewer-surface"] canvas')).toBeVisible({ timeout: 20_000 })

  await expect(page.locator('[data-testid="question-card"]')).toContainText(EXCEL_LABEL)
  await expect(page.locator('[data-testid="family-select"]')).toHaveValue(EXCEL_FAMILY)
  await expect(page.locator('[data-testid="level-select"]')).toHaveValue('1')
  await expect(page.locator('[data-testid="seed-input"]')).toHaveValue('0')

  const viewerSurface = page.locator('[data-testid="viewer-surface"]')
  await expect(viewerSurface).toHaveAttribute('data-active-sheet-id', 'examples')
  await expect(viewerSurface).toHaveAttribute('data-current-page-id', 'examples-p1')
  await expect(viewerSurface).toHaveAttribute('data-zoom-index', '0')
  await expect(viewerSurface).toHaveAttribute('data-viewbox', /"width"/)
})

test('invalid dev-family URL falls back to public benchmark instance startup', async ({ page }) => {
  await page.goto(`/?family=${EXCEL_FAMILY}&level=99&seed=0`, { waitUntil: 'domcontentloaded' })
  await expect(page.locator('[data-testid="viewer-surface"] canvas')).toBeVisible({ timeout: 20_000 })

  await expect(page.locator('[data-testid="question-card"]')).not.toContainText(EXCEL_LABEL)
  await expect(page.locator('[data-testid="family-select"]')).toHaveValue('marker_position_rule_transfer')
  await expect(page.locator('[data-testid="instance-select"]')).not.toHaveValue('')
})
