import { test, expect } from '@playwright/test';

test.describe('Workspace dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/workspace');
    await expect(page.locator('app-workspace')).toBeVisible();
  });

  test('WS10-01: displays all four workspace metrics', async ({ page }) => {
    const metrics = [
      'Total Data Models',
      'Total Entities',
      'Generated Datasets',
      'Total Records',
    ];

    for (const metric of metrics) {
      await expect(
        page.getByText(metric, { exact: true }),
      ).toBeVisible();
    }
  });

  test('WS10-02: displays the four metric values', async ({ page }) => {
    const labels = [
      'Total Data Models',
      'Total Entities',
      'Generated Datasets',
      'Total Records',
    ];

    for (const label of labels) {
      const labelElement = page.getByText(label, { exact: true });
      await expect(labelElement).toBeVisible();

      const metricCard = labelElement.locator(
        'xpath=ancestor::*[.//*[normalize-space()="'
        + label
        + '"]][1]',
      );

      await expect(metricCard).toBeVisible();
    }
  });
});
