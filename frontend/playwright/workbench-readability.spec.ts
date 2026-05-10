import { expect, test } from '@playwright/test'

import { createConsoleCollector, dumpFailureArtifacts, rectBottom } from './readability-helpers'

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

test('workbench readability states', async ({ page }, testInfo) => {
  const root = page.locator('#root')
  const viewerCanvas = page.locator('[data-testid="viewer-surface"] canvas')
  const questionCard = page.locator('[data-testid="question-card"]')
  const viewerPanel = page.locator('[data-testid="viewer-panel"]')
  const answerCard = page.locator('[data-testid="answer-card"]')
  const inspectorPanel = page.locator('[data-testid="inspector-panel"]')
  const pageLabel = page.locator('[data-testid="page-label"]')
  const nextPageButton = page.locator('[data-testid="next-page-button"]')
  const sheetButtons = page.locator('[data-testid="sheet-tab-button"]')
  const consoleMessages = createConsoleCollector(page)
  const suffix = testInfo.project.name.replace(/^chromium-/, '')

  try {
    await page.goto('/', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('한국어 Visual TableQA Workbench')).toBeVisible()
    await viewerCanvas.waitFor({ state: 'visible', timeout: 20_000 })
    await expect(page.getByText('세션을 불러오는 중입니다.')).not.toBeVisible()

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

    const consoleErrors = filterConsoleMessages(consoleMessages)
    expect(consoleErrors).toEqual([])

    await page.getByRole('button', { name: 'Inspector 열기' }).click()
    await expect(page.getByText('보조 정보와 기록')).toBeVisible()
    await expect(inspectorPanel).toBeVisible()

    await page.getByRole('button', { name: '닫기' }).click()
    await expect(page.getByText('보조 정보와 기록')).not.toBeVisible()
    await expect(root).toBeVisible()

    const querySheetButton = page.locator('[data-testid="sheet-tab-button"][data-sheet-name="질의"]')
    if (await querySheetButton.count()) {
      if (!(await querySheetButton.isDisabled())) {
        await querySheetButton.click()
        await expect
          .poll(async () => ((await pageLabel.textContent()) ?? '').includes('질의'))
          .toBeTruthy()
      }
      await expect(root).toBeVisible()
    }

    const sheetCount = await sheetButtons.count()
    let multiPageCovered = false
    for (let index = 0; index < sheetCount; index += 1) {
      const button = sheetButtons.nth(index)
      if (await button.isDisabled()) {
        const currentInfo = parsePageLabel((await pageLabel.textContent()) ?? '')
        if (!currentInfo || currentInfo.total <= 1) {
          continue
        }
      } else {
        await button.click()
        await expect(viewerCanvas).toBeVisible()
      }

      const info = parsePageLabel((await pageLabel.textContent()) ?? '')
      if (!info || info.total <= 1) {
        continue
      }

      await nextPageButton.click()
      await expect
        .poll(async () => parsePageLabel((await pageLabel.textContent()) ?? '')?.current ?? 0)
        .toBeGreaterThan(info.current)

      await expect(root).toBeVisible()
      multiPageCovered = true
      break
    }

    testInfo.annotations.push({
      type: 'multi-page',
      description: multiPageCovered ? 'next_page readability covered' : 'no multi-page sheet in current benchmark',
    })
  } catch (error) {
    await dumpFailureArtifacts(page, testInfo, `workbench-${suffix}`, {
      consoleMessages,
      locator: root,
    })
    throw error
  }
})
