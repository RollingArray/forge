import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';

const authFile = path.join(
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
      outputFolder: 'playwright-report/workspace-archived',
      open: 'never',
    }],
  ],

  outputDir: 'test-results/workspace-archived-e2e',
  timeout: 180_000,

  expect: {
    timeout: 15_000,
  },

  use: {
    baseURL: 'http://127.0.0.1:18866',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'archived-owner-setup',
      testMatch: '**/isolated/auth.setup.ts',
    },
    {
      name: 'workspace-archived-owner',
      testMatch: '**/workspace/**/*.spec.ts',
      dependencies: ['archived-owner-setup'],
      use: {
        ...devices['Desktop Chrome'],
        storageState: authFile,
      },
    },
  ],
});
