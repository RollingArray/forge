import { test, expect } from '@playwright/test';
import path from 'node:path';
import { mkdir, readFile, writeFile } from 'node:fs/promises';

const sessionsFile = path.resolve(
  __dirname,
  '../playwright/.auth/local-sessions.json',
);

const authFile = path.resolve(
  __dirname,
  '../playwright/.auth/local-owner.json',
);

const baseURL = process.env.FORGE_E2E_BASE_URL ?? 'http://localhost:4200';

test('authenticate as local FORGE E2E Owner', async () => {
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
      origin: new URL(baseURL).origin,
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

});
