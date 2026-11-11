import { test, expect } from '@playwright/test';
import path from 'node:path';
import { mkdir, readFile, writeFile } from 'node:fs/promises';

const baseURL =
  process.env.FORGE_E2E_BASE_URL ?? 'http://127.0.0.1:18876';

const sessionsFile = path.resolve(
  process.env.FORGE_E2E_SESSIONS_FILE ??
    path.resolve(__dirname, '../../../dist/test-runs/sessions.json'),
);

const authFile = path.resolve(
  __dirname,
  '../../playwright/.auth/isolated-owner.json',
);

test('authenticate as isolated FORGE E2E Owner', async () => {
  const sessions = JSON.parse(await readFile(sessionsFile, 'utf8'));
  const session = sessions.owner;

  expect(session).toMatchObject({
    tokenType: 'Bearer',
    user: {
      email: 'forge.owner@collins.com',
      displayName: 'FORGE E2E Owner',
    },
  });
  expect(session.accessToken.length).toBeGreaterThan(0);
  expect(session.user.userId.length).toBeGreaterThan(0);

  const storageState = {
    cookies: [],
    origins: [{
      origin: baseURL,
      localStorage: [{
        name: 'forge.auth.session',
        value: JSON.stringify(session),
      }],
    }],
  };

  await mkdir(path.dirname(authFile), { recursive: true });
  await writeFile(authFile, JSON.stringify(storageState, null, 2), {
    mode: 0o600,
  });

  console.log('PASS: Isolated FORGE Owner session loaded.');
  console.log('PASS: Isolated Playwright storage state saved.');
});
