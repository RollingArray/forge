import { test, expect, type BrowserContext } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const BASE_URL =
  process.env.FORGE_E2E_BASE_URL ?? 'http://127.0.0.1:18876';

const BOOTSTRAP_KEY_PATH = resolve(
  process.env.FORGE_E2E_BOOTSTRAP_KEY_FILE ??
    resolve(__dirname, '../../../dist/forge-e2e/e2e-bootstrap.key'),
);

const bootstrapKey = readFileSync(BOOTSTRAP_KEY_PATH, 'utf8').trim();

if (!bootstrapKey) {
  throw new Error('E2E bootstrap key is empty.');
}

const identities = [
  {
    identity: 'owner',
    email: 'forge.owner@collins.com',
    displayName: 'FORGE E2E Owner',
  },
  {
    identity: 'contributor',
    email: 'forge.contributor@collins.com',
    displayName: 'FORGE E2E Contributor',
  },
  {
    identity: 'viewer',
    email: 'forge.viewer@collins.com',
    displayName: 'FORGE E2E Viewer',
  },
] as const;

const workspaceEndpoints = [
  '/api/v1/workspace/metrics',
  '/api/v1/data-models',
  '/api/v1/workspace/templates',
  '/api/v1/workspace/activity',
];

test('Owner, Contributor and Viewer authenticate independently and load Workspace', async ({
  browser,
  request,
}) => {
  const userIds = new Set<string>();

  for (const identity of identities) {
    let context: BrowserContext | undefined;

    try {
      const bootstrapResponse = await request.post(
        `${BASE_URL}/api/v1/__e2e/auth/session`,
        {
          headers: {
            'X-FORGE-E2E-KEY': bootstrapKey,
          },
          data: {
            identity: identity.identity,
          },
        },
      );

      expect(
        bootstrapResponse.status(),
        `${identity.identity}: bootstrap session`,
      ).toBe(200);

      const session = await bootstrapResponse.json();

      expect(session.accessToken).toBeTruthy();
      expect(session.tokenType).toBe('Bearer');
      expect(session.user.email).toBe(identity.email);
      expect(session.user.displayName).toBe(identity.displayName);
      expect(session.user.userId).toBeTruthy();

      userIds.add(session.user.userId);

      const authorization = {
        Authorization: `Bearer ${session.accessToken}`,
      };

      for (const endpoint of workspaceEndpoints) {
        const response = await request.get(`${BASE_URL}${endpoint}`, {
          headers: authorization,
        });

        expect(
          response.status(),
          `${identity.identity}: GET ${endpoint}`,
        ).toBeGreaterThanOrEqual(200);

        expect(
          response.status(),
          `${identity.identity}: GET ${endpoint}`,
        ).toBeLessThan(300);
      }

      context = await browser.newContext();

      await context.addInitScript((storedSession) => {
        window.localStorage.setItem(
          'forge.auth.session',
          JSON.stringify(storedSession),
        );
      }, session);

      const page = await context.newPage();

      await page.goto(`${BASE_URL}/workspace`);

      await expect(page.locator('.user-name')).toHaveText(
        identity.displayName,
      );

      await expect(page.locator('app-workspace-welcome-header')).toBeVisible();

      console.log(
        `PASS: ${identity.identity} | ${identity.email} | ` +
        `unique user ID | 4 Workspace APIs | Workspace loaded`,
      );
    } finally {
      await context?.close();
    }
  }

  expect(userIds.size).toBe(3);
  console.log('PASS: All three roles have distinct backend user identities.');
});
