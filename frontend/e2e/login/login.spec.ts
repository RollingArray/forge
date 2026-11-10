import { test, expect } from '@playwright/test';

const TEST_EMAIL = 'forge.e2e@example.com';

test.describe('S01 - Login', () => {
  test.use({
    storageState: {
      cookies: [],
      origins: []
    }
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/login', { waitUntil: 'networkidle' });
  });

  test('LG-01: renders login screen and required controls', async ({ page }) => {
    await expect(page).toHaveTitle('FORGE');
    await expect(page.locator('#email')).toBeVisible();
    await expect(page.getByRole('button', { name: /Send sign-in link/ })).toBeVisible();
    await expect(page.getByText(/Technical Data Strictly Prohibited/i)).toBeVisible();
  });

  test('LG-02: prevents submission when email is empty', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Send sign-in link/ })).toBeDisabled();
  });

  test('LG-03: rejects malformed email addresses', async ({ page }) => {
    const email = page.locator('#email');
    const button = page.getByRole('button', { name: /Send sign-in link/ });

    await email.fill('not-an-email');

    const valid = await email.evaluate((el: HTMLInputElement) => el.checkValidity());

    expect(valid).toBe(false);
    await expect(button).toBeDisabled();
  });

  test('LG-04: enables submission for a valid email address', async ({ page }) => {
    await page.locator('#email').fill(TEST_EMAIL);
    await expect(page.getByRole('button', { name: /Send sign-in link/ })).toBeEnabled();
  });

  test('LG-05: displays confirmation after successful request', async ({ page }) => {
    let requestCount = 0;

    await page.route('**/api/**', async route => {
      requestCount += 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: '{}'
      });
    });

    await page.locator('#email').fill(TEST_EMAIL);
    await page.getByRole('button', { name: /Send sign-in link/ }).click();

    await expect(page.getByText(/Sign-in link sent/i)).toBeVisible();
    await expect(page.getByText(TEST_EMAIL)).toBeVisible();
    expect(requestCount).toBe(1);
  });

  test('LG-06: displays an error for HTTP 403', async ({ page }) => {
    await page.route('**/api/**', async route => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Forbidden' })
      });
    });

    await page.locator('#email').fill(TEST_EMAIL);
    await page.getByRole('button', { name: /Send sign-in link/ }).click();

    await expect(page.getByRole('alert')).toBeVisible();
  });

  test('LG-07: displays an error for HTTP 500', async ({ page }) => {
    await page.route('**/api/**', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' })
      });
    });

    await page.locator('#email').fill(TEST_EMAIL);
    await page.getByRole('button', { name: /Send sign-in link/ }).click();

    await expect(page.getByRole('alert')).toBeVisible();
  });

  test('LG-08: handles a network failure', async ({ page }) => {
    await page.route('**/api/**', async route => {
      await route.abort('failed');
    });

    await page.locator('#email').fill(TEST_EMAIL);
    await page.getByRole('button', { name: /Send sign-in link/ }).click();

    await expect(page.getByRole('alert')).toBeVisible();
  });

  test('LG-09: allows changing email after successful request', async ({ page }) => {
    await page.route('**/api/**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: '{}'
      });
    });

    await page.locator('#email').fill(TEST_EMAIL);
    await page.getByRole('button', { name: /Send sign-in link/ }).click();

    await expect(page.getByText(/Sign-in link sent/i)).toBeVisible();

    await page.getByRole('button', { name: /Use a different email/i }).click();

    await expect(page.locator('#email')).toBeVisible();
    await expect(page.locator('#email')).toHaveValue(TEST_EMAIL);

    await page.locator('#email').fill('another.user@example.com');
    await expect(page.getByRole('button', {
      name: /Send sign-in link/
    })).toBeEnabled();
  });

  test('LG-10: disables controls and prevents duplicate requests while pending', async ({ page }) => {
    let requestCount = 0;
    let releaseRequest!: () => void;

    const requestGate = new Promise<void>(resolve => {
      releaseRequest = resolve;
    });

    await page.route('**/auth/magic-link', async route => {
      requestCount += 1;
      await requestGate;

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: '{}'
      });
    });

    const email = page.locator('#email');
    const button = page.locator('button.continue-button').first();

    await email.fill(TEST_EMAIL);
    await button.click();

    await expect.poll(() => requestCount).toBe(1);

    await expect(button).toContainText('Sending link...');
    await expect(button).toBeDisabled();
    await expect(email).toBeDisabled();

    // A second click must not produce another request.
    await button.click({ force: true });
    expect(requestCount).toBe(1);

    releaseRequest();

    await expect(page.getByText(/Sign-in link sent/i)).toBeVisible();
    expect(requestCount).toBe(1);
  });
});
