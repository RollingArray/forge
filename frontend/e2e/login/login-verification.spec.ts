import { test, expect } from '@playwright/test';

test.describe('S01 - Magic Link Verification', () => {
  test.use({
    storageState: {
      cookies: [],
      origins: []
    }
  });

  test('LG-11: displays an error when the verification token is missing', async ({ page }) => {
    await page.goto('/login/verify', { waitUntil: 'networkidle' });

    await expect(page.getByRole('heading', { name: 'Unable to sign in' })).toBeVisible();
    await expect(page.getByRole('button', {
      name: /request a new link/i
    })).toBeVisible();
  });

  test('LG-12: displays an error when the verification token is invalid or expired', async ({ page }) => {
    let verificationRequestCount = 0;

    await page.route('**/auth/magic-link/verify', async route => {
      verificationRequestCount += 1;

      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Invalid or expired token'
        })
      });
    });

    await page.goto('/login/verify?token=invalid-e2e-token', {
      waitUntil: 'networkidle'
    });

    await expect.poll(() => verificationRequestCount).toBe(1);
    await expect(page.getByRole('heading', { name: 'Unable to sign in' })).toBeVisible();
    await expect(page.getByRole('button', {
      name: /request a new link/i
    })).toBeVisible();
  });

  test('LG-13: request-new-link action returns the user to Login', async ({ page }) => {
    await page.route('**/auth/magic-link/verify', async route => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Invalid or expired token'
        })
      });
    });

    await page.goto('/login/verify?token=invalid-e2e-token', {
      waitUntil: 'networkidle'
    });

    await expect(page.getByRole('button', {
      name: /request a new link/i
    })).toBeVisible();

    await page.getByRole('button', {
      name: /request a new link/i
    }).click();

    await expect(page).toHaveURL(/\/login$/);
    await expect(page.locator('#email')).toBeVisible();
  });

  test('LG-14: persists the verified session and navigates to Workspace', async ({ page }) => {
    const session = {
      accessToken: 'e2e-mocked-access-token',
      tokenType: 'Bearer',
      user: {
        userId: 'e2e-user-001',
        email: 'forge.e2e@example.com',
        displayName: 'FORGE E2E User',
        employeeId: 'E2E001',
        profile: {}
      }
    };

    // Mock only the verification endpoint for this UI contract test.
    await page.route('**/auth/magic-link/verify', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(session)
      });
    });

    // Workspace APIs must return valid responses because the session above
    // contains a test token that is not recognized by the real backend.
    const workspaceResponses = [
      {
        url: '**/api/v1/workspace/metrics',
        body: {
          total_data_models: 0,
          total_entities: 0,
          generated_datasets: 0,
          total_records: 0
        }
      },
      {
        url: '**/api/v1/data-models',
        body: []
      },
      {
        url: '**/api/v1/workspace/templates',
        body: []
      },
      {
        url: '**/api/v1/workspace/activity',
        body: []
      }
    ];

    for (const response of workspaceResponses) {
      await page.route(response.url, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(response.body)
        });
      });
    }

    await page.goto('/login/verify?token=valid-e2e-token', {
      waitUntil: 'networkidle'
    });

    const storedSession = await page.evaluate(() => {
      const value = localStorage.getItem('forge.auth.session');
      return value ? JSON.parse(value) : null;
    });

    expect(storedSession).toEqual(session);

    await expect(page).toHaveURL(/\/workspace$/);
    await expect(page.locator('.user-name')).toHaveText('FORGE E2E User');
  });

  test('LG-15: displays organization profile lookup failure for HTTP 502', async ({ page }) => {
    await page.route('**/auth/magic-link/verify', async route => {
      await route.fulfill({
        status: 502,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Organization profile lookup failed' })
      });
    });

    await page.goto('/login/verify?token=profile-error-token', {
      waitUntil: 'networkidle'
    });

    await expect(page.getByRole('heading', {
      name: 'Unable to sign in'
    })).toBeVisible();

    await expect(page.getByText(
      /could not retrieve your organization profile/i
    )).toBeVisible();

    await expect(page.getByRole('button', {
      name: /request a new link/i
    })).toBeVisible();

    expect(await page.evaluate(
      () => localStorage.getItem('forge.auth.session')
    )).toBeNull();
  });

  for (const status of [400, 403, 404]) {
    test(`LG-16: handles invalid or expired verification links with HTTP ${status}`, async ({ page }) => {
      await page.route('**/auth/magic-link/verify', async route => {
        await route.fulfill({
          status,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid or expired token' })
        });
      });

      await page.goto('/login/verify?token=invalid-e2e-token', {
        waitUntil: 'networkidle'
      });

      await expect(page.getByRole('heading', {
        name: 'Unable to sign in'
      })).toBeVisible();

      await expect(page.getByText(
        /sign-in link/i
      )).toBeVisible();

      await expect(page.getByRole('button', {
        name: /request a new link/i
      })).toBeVisible();

      expect(await page.evaluate(
        () => localStorage.getItem('forge.auth.session')
      )).toBeNull();
    });
  }

  test('LG-17: handles network failure without creating a session', async ({ page }) => {
    await page.route('**/auth/magic-link/verify', async route => {
      await route.abort('failed');
    });

    await page.goto('/login/verify?token=network-error-token', {
      waitUntil: 'networkidle'
    });

    await expect(page.getByRole('heading', {
      name: 'Unable to sign in'
    })).toBeVisible();

    await expect(page.getByText(
      /unable to connect to/i
    )).toBeVisible();

    await expect(page.getByRole('button', {
      name: /request a new link/i
    })).toBeVisible();

    expect(await page.evaluate(
      () => localStorage.getItem('forge.auth.session')
    )).toBeNull();
  });

});
