import { defineConfig } from '@playwright/test'
import path from 'node:path'

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:5173'
const enableWorkbenchServers = process.env.PLAYWRIGHT_ENABLE_WORKBENCH !== '0'
const reviewDir = process.env.PLAYWRIGHT_REVIEW_DIR ? path.resolve(process.cwd(), process.env.PLAYWRIGHT_REVIEW_DIR) : null
const staticPort = Number(process.env.PLAYWRIGHT_STATIC_PORT ?? '8781')
const webServer = []

if (enableWorkbenchServers) {
  webServer.push(
    {
      command: 'uv run python -m table_env_bench.scripts.run_server --host 127.0.0.1 --port 8000',
      url: 'http://127.0.0.1:8000/api/catalog',
      reuseExistingServer: true,
      timeout: 120_000,
      cwd: '..',
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173',
      url: baseURL,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  )
}

if (reviewDir) {
  webServer.push({
    command: `python3 -m http.server ${staticPort} --bind 127.0.0.1 --directory "${reviewDir}"`,
    url: `http://127.0.0.1:${staticPort}/review.html`,
    reuseExistingServer: true,
    timeout: 120_000,
    cwd: '..',
  })
}

export default defineConfig({
  testDir: './playwright',
  timeout: 30_000,
  fullyParallel: false,
  reporter: [['list']],
  webServer,
  use: {
    baseURL,
    trace: 'off',
    screenshot: 'off',
  },
  projects: [
    {
      name: 'chromium-fullhd',
      use: {
        browserName: 'chromium',
        viewport: {
          width: 1920,
          height: 1080,
        },
      },
    },
    {
      name: 'chromium-qhd',
      use: {
        browserName: 'chromium',
        viewport: {
          width: 2560,
          height: 1440,
        },
      },
    },
  ],
})
