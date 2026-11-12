import { test, expect } from '@playwright/test';

const BASE_EMAIL = 'ranjoy.sen@collins.com';

const WORKSPACE_ENDPOINTS = [
  '/api/v1/workspace/metrics',
  '/api/v1/data-models',
  '/api/v1/workspace/templates',
  '/api/v1/workspace/activity',
];

test.describe('LG03 - Real Email Authentication', () => {
  test('LG03-01: corporate magic link authenticates and loads Workspace', async ({ page }) => {
    test.setTimeout(7 * 60 * 1000);

    let magicLinkRequestCount = 0;
    let verificationStatus: number | undefined;

    const workspaceStatuses = new Map<string, number>();

    page.on('request', (request) => {
      const url = new URL(request.url());

      if (url.pathname === '/api/v1/auth/magic-link' && request.method() === 'POST') {
        magicLinkRequestCount += 1;
      }
    });

    page.on('response', (response) => {
      const url = new URL(response.url());

      if (url.pathname === '/api/v1/auth/magic-link/verify') {
        verificationStatus = response.status();
      }

      if (WORKSPACE_ENDPOINTS.includes(url.pathname)) {
        workspaceStatuses.set(url.pathname, response.status());
      }
    });

    // Start with a clean, unauthenticated browser session.
    await page.goto('/login', { waitUntil: 'networkidle' });
    await expect(page.locator('#email')).toBeVisible();

    // Submit one real magic-link request through the UI.
    await page.locator('#email').fill(BASE_EMAIL);

    const sendResponsePromise = page.waitForResponse((response) => {
      const url = new URL(response.url());

      return url.pathname === '/api/v1/auth/magic-link' && response.request().method() === 'POST';
    });

    await page
      .getByRole('button', {
        name: /Send sign-in link/i,
      })
      .click();

    const sendResponse = await sendResponsePromise;

    expect(sendResponse.status()).toBe(200);
    expect(magicLinkRequestCount).toBe(1);

    await expect(page.getByText(/Sign-in link sent/i)).toBeVisible();
    await expect(page.getByText(BASE_EMAIL)).toBeVisible();

    console.log('');
    console.log('REAL EMAIL REQUEST: accepted by the isolated backend.');
    console.log('EMAIL: ' + BASE_EMAIL);
    console.log('');
    console.log('ACTION REQUIRED:');
    console.log('1. Open the actual email delivered to your mailbox.');
    console.log('2. Copy the complete magic link.');
    console.log('3. Switch to the visible FORGE Chromium browser.');
    console.log('4. Paste the link into the browser address bar and press Enter.');
    console.log('');
    console.log('The test is waiting for the real verification and Workspace redirect.');
    console.log('Do not paste the link into this terminal.');
    console.log('');

    // Do not navigate programmatically or inject a token.
    // The user manually pastes the real email URL into the visible browser.
    await page.bringToFront();

    await page.waitForFunction(() => window.location.pathname === '/workspace', null, {
      timeout: 240_000,
      polling: 500,
    });

    // Confirm that the backend accepted the actual email token.
    expect(verificationStatus).toBe(200);

    // Confirm that all four real Workspace API requests succeeded.
    await expect
      .poll(() => workspaceStatuses.size, { timeout: 30_000 })
      .toBe(WORKSPACE_ENDPOINTS.length);

    for (const endpoint of WORKSPACE_ENDPOINTS) {
      const status = workspaceStatuses.get(endpoint);

      expect(status, 'Workspace API failed: ' + endpoint).toBeGreaterThanOrEqual(200);

      expect(status, 'Workspace API failed: ' + endpoint).toBeLessThan(300);
    }

    // Read session properties without exposing the actual JWT.
    const sessionSummary = await page.evaluate(() => {
      const stored = localStorage.getItem('forge.auth.session');

      if (!stored) {
        return null;
      }

      const session = JSON.parse(stored);

      return {
        hasAccessToken: typeof session.accessToken === 'string' && session.accessToken.length > 0,
        tokenType: session.tokenType,
        email: session.user?.email,
        displayName: session.user?.displayName,
      };
    });

    expect(sessionSummary).not.toBeNull();
    expect(sessionSummary?.hasAccessToken).toBe(true);
    expect(sessionSummary?.tokenType).toBe('Bearer');
    expect(sessionSummary?.email?.toLowerCase()).toBe(BASE_EMAIL);
    expect(sessionSummary?.displayName?.trim().length).toBeGreaterThan(0);

    await expect(page).toHaveURL(/\/workspace$/);
    await expect(page.locator('.user-name')).toHaveText(sessionSummary!.displayName);
  });
});
