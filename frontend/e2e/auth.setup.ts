import { test, expect } from '@playwright/test';
import path from 'node:path';

const authFile = path.join(
  __dirname,
  '..',
  'playwright',
  '.auth',
  'user.json',
);

test('authenticate through the normal FORGE login flow', async ({ page }) => {
  test.setTimeout(5 * 60 * 1000);

  await page.goto('/login');

  console.log('');
  console.log('==============================================');
  console.log('FORGE AUTHENTICATION REQUIRED');
  console.log('Complete the normal magic-link login in the browser.');
  console.log('Playwright will save the authenticated session.');
  console.log('==============================================');
  console.log('');

  await page.waitForURL(
    (url) => url.pathname === '/workspace' ||
             url.pathname.startsWith('/workspace/'),
    { timeout: 5 * 60 * 1000 },
  );

  await expect(page).toHaveURL(/\/workspace/);

  await page.context().storageState({
    path: authFile,
  });

  console.log('FORGE authentication state saved locally.');
});
