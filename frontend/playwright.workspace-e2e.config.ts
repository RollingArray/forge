import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { existsSync } from 'node:fs';

const authFile = path.join(
  __dirname,
  'playwright',
  '.auth',
  'user.json',
);

const hasAuthState = existsSync(authFile);

export default defineConfig({
  testDir: './e2e',
  testMatch: ['workspace/**/*.spec.ts'],
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,

  reporter: [
    ['list'],
    ['html', {
      outputFolder: 'playwright-report/workspace',
      open: 'never',
    }],
  ],

  outputDir: 'test-results/workspace-e2e',
  timeout: 180_000,

  expect: {
    timeout: 15_000,
  },

  use: {

    baseURL: 'http://localhost:4200',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    ...(!hasAuthState
      ? [{
          name: 'setup',
          testMatch: '**/*.setup.ts',
        }]
      : []),

    {
      name: 'chromium',
      testIgnore: '**/*.setup.ts',
      ...(hasAuthState ? {} : { dependencies: ['setup'] }),
      use: {
        ...devices['Desktop Chrome'],
        storageState: authFile,
      },
    },
  ],
});
