import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';

const baseURL =
  process.env.FORGE_E2E_BASE_URL ?? 'http://127.0.0.1:18876';

const authFile = path.resolve(
  __dirname,
  'playwright',
  '.auth',
  'isolated-owner.json',
);

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [
    ['list'],
    ['html', {
      outputFolder: process.env.FORGE_E2E_EVIDENCE_DIR
        ? path.resolve(process.env.FORGE_E2E_EVIDENCE_DIR, 'playwright-report')
        : 'playwright-report/isolated-e2e',
      open: 'never',
    }],
  ],
  outputDir: process.env.FORGE_E2E_EVIDENCE_DIR
    ? path.resolve(process.env.FORGE_E2E_EVIDENCE_DIR, 'test-results')
    : 'test-results/isolated-e2e',
  timeout: 180_000,
  expect: {
    timeout: 15_000,
  },
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'on',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'isolated-auth-setup',
      testMatch: '**/isolated/auth.setup.ts',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'login',
      testMatch: '**/login/**/*.spec.ts',
      use: {
        ...devices['Desktop Chrome'],
        storageState: { cookies: [], origins: [] },
      },
    },
    {
      name: 'multi-user',
      testMatch: '**/multi-user/**/*.spec.ts',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'workspace',
      testMatch: '**/workspace/**/*.spec.ts',
      dependencies: ['isolated-auth-setup'],
      use: {
        ...devices['Desktop Chrome'],
        storageState: authFile,
      },
    },
    {
      name: 'wp02',
      testMatch: '**/wp02-model-setup.spec.ts',
      dependencies: ['isolated-auth-setup'],
      use: {
        ...devices['Desktop Chrome'],
        storageState: authFile,
      },
    },
    {
      name: 'real-email',
      testMatch: '**/real-email/**/*.spec.ts',
      timeout: 7 * 60 * 1000,
      use: {
        ...devices['Desktop Chrome'],
        headless: false,
        launchOptions: {
          slowMo: 150,
        },
        storageState: {
          cookies: [],
          origins: [],
        },
        trace: 'off',
        screenshot: 'off',
        video: 'off',
      },
    },
  ],
});
