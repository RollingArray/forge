import { test, expect } from '@playwright/test';
import path from 'node:path';
import { mkdir, readFile, writeFile } from 'node:fs/promises';

const e2eRoot = path.resolve(
  process.env.FORGE_E2E_ROOT ?? path.resolve(__dirname, '../../../dist/forge-e2e'),
);

const baseURL =
  process.env.FORGE_E2E_BASE_URL ?? 'http://127.0.0.1:18876';

const keyFile = path.resolve(
  process.env.FORGE_E2E_BOOTSTRAP_KEY_FILE ??
    path.join(e2eRoot, 'e2e-bootstrap.key'),
);

const authFile = path.resolve(
  __dirname,
  '../../playwright/.auth/isolated-owner.json',
);

test('authenticate as isolated FORGE E2E Owner', async ({ request }) => {
  const bootstrapKey = (await readFile(keyFile, 'utf8')).trim();

  expect(bootstrapKey.length).toBeGreaterThan(0);

  const response = await request.post(
    '/api/v1/__e2e/auth/session',
    {
      headers: {
        'X-Forge-E2E-Key': bootstrapKey,
      },
      data: {
        identity: 'owner',
      },
    },
  );

  expect(
    response.status(),
    'Isolated E2E Owner authentication should succeed',
  ).toBe(200);

  const session: unknown = await response.json();

  expect(session).toMatchObject({
    tokenType: 'Bearer',
    user: {
      email: 'forge.owner@collins.com',
      displayName: 'FORGE E2E Owner',
    },
  });

  const sessionData = session as {
    accessToken: string;
    tokenType: string;
    user: {
      userId: string;
      email: string;
      displayName: string;
    };
  };

  expect(sessionData.accessToken.length).toBeGreaterThan(0);
  expect(sessionData.user.userId.length).toBeGreaterThan(0);

  const storageState = {
    cookies: [],
    origins: [
      {
        origin: baseURL,
        localStorage: [
          {
            name: 'forge.auth.session',
            value: JSON.stringify(session),
          },
        ],
      },
    ],
  };

  await mkdir(path.dirname(authFile), { recursive: true });

  await writeFile(
    authFile,
    JSON.stringify(storageState, null, 2),
    { mode: 0o600 },
  );

  console.log('PASS: Isolated FORGE Owner session created.');
  console.log('PASS: Isolated Playwright storage state saved.');
});
