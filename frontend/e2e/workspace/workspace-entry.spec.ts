import { test, expect } from '@playwright/test';

test.describe('WS01 - Workspace Entry', () => {
  test('WS01-01: authenticated user can open Workspace', async ({ page }) => {
    await page.goto('/workspace');

    await expect(page).toHaveURL(/\/workspace\/?$/);
    await expect(page.locator('app-workspace')).toBeVisible();
  });

  test('WS01-02: Workspace loads all four dashboard data sources', async ({ page }) => {
    const endpoints = [
      '/api/v1/workspace/metrics',
      '/api/v1/data-models',
      '/api/v1/workspace/templates',
      '/api/v1/workspace/activity',
    ];

    const responses = endpoints.map((endpoint) =>
      page.waitForResponse((response) =>
        response.url().includes(endpoint) &&
        response.request().method() === 'GET',
      ),
    );

    await page.goto('/workspace');

    const results = await Promise.all(responses);

    for (const response of results) {
      expect(
        response.status(),
        `${response.url()} should load successfully`,
      ).toBe(200);
    }
  });

  test('WS01-03: Workspace survives a browser refresh', async ({ page }) => {
    await page.goto('/workspace');
    await expect(page.locator('app-workspace')).toBeVisible();

    await page.reload();

    await expect(page).toHaveURL(/\/workspace\/?$/);
    await expect(page.locator('app-workspace')).toBeVisible();
  });
});
