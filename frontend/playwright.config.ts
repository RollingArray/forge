import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';

const authFile = path.join(
  __dirname,
  'playwright',
  '.auth',
  'local-owner.json',
);

// Visual slowdown is enabled only for explicitly headed test runs.
const isHeadedRun = process.argv.includes('--headed');
const slowMoMs = isHeadedRun
  ? Math.max(0, Number(process.env.FORGE_E2E_SLOW_MO_MS ?? 0) || 0)
  : 0;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,

  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],

  timeout: 180_000,

  expect: {
    timeout: 15_000,
  },

  use: {
    baseURL: process.env.FORGE_E2E_BASE_URL ?? 'http://localhost:4200',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'local-auth',
      testMatch: '**/local-auth.setup.ts',
      testIgnore: '**/isolated/**',
    },
    {
      name: 'chromium',
      testIgnore: [
        '**/*.setup.ts',
        '**/isolated/**',
        '**/multi-user/**',
        '**/real-email/**',
        '**/*demo*.spec.ts',
      ],
      dependencies: ['local-auth'],
      use: {
        ...devices['Desktop Chrome'],
        storageState: authFile,
        ...(slowMoMs > 0
          ? { launchOptions: { slowMo: slowMoMs } }
          : {}),
      },
    },
  ],
});
