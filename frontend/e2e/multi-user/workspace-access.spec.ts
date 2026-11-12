import { test, expect, type BrowserContext, type Page, type TestInfo } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const BASE_URL = process.env.FORGE_E2E_BASE_URL ?? 'http://127.0.0.1:18876';

const SESSIONS_FILE = resolve(
  process.env.FORGE_E2E_SESSIONS_FILE ??
    resolve(__dirname, '../../../dist/test-runs/sessions.json'),
);

function loadE2eSessions(): Record<string, any> {
  return JSON.parse(readFileSync(SESSIONS_FILE, 'utf8')) as Record<string, any>;
}

async function attachPassScreenshot(testInfo: TestInfo, page: Page, label: string): Promise<void> {
  const screenshotPath = testInfo.outputPath(`passed-${label}.png`);

  await page.screenshot({
    path: screenshotPath,
    fullPage: true,
  });

  await testInfo.attach(`passed-${label}`, {
    path: screenshotPath,
    contentType: 'image/png',
  });
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

test.describe('MU01 - Workspace Access', () => {
  test('MU01-01: Owner, Contributor and Viewer authenticate independently and load Workspace', async ({
    browser,
    request,
  }, testInfo) => {
    const e2eSessions = loadE2eSessions();
    const userIds = new Set<string>();

    await test.step('MU01-S01: Verify all three identities independently', async () => {
      for (const identity of identities) {
        let context: BrowserContext | undefined;

        try {
          const session = e2eSessions[identity.identity];

          await test.step(`${identity.identity}: validate session and Workspace APIs`, async () => {
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

              expect(response.status(), `${identity.identity}: GET ${endpoint}`).toBeLessThan(300);
            }
          });

          await test.step(`${identity.identity}: authenticate and load Workspace`, async () => {
            context = await browser.newContext();

            await context.addInitScript((storedSession) => {
              window.localStorage.setItem('forge.auth.session', JSON.stringify(storedSession));
            }, session);

            const page = await context.newPage();
            await page.goto(`${BASE_URL}/workspace`);

            await expect(page.locator('.user-name')).toHaveText(identity.displayName);

            await expect(page.locator('app-workspace-welcome-header')).toBeVisible();

            await attachPassScreenshot(testInfo, page, `${identity.identity}-workspace`);
          });
        } finally {
          await context?.close();
        }
      }
    });

    await test.step('MU01-S02: Verify distinct backend user identities', async () => {
      expect(userIds.size).toBe(3);
    });
  });

  test('MU01-02: Owner shares a Data Model with Contributor and Viewer', async ({
    browser,
    request,
  }, testInfo) => {
    const e2eSessions = loadE2eSessions();
    const sessions: Record<string, any> = {};
    const contexts: BrowserContext[] = [];
    const pages: Record<string, import('@playwright/test').Page> = {};
    let modelName = '';

    try {
      // Bootstrap all identities before starting user search.
      for (const identity of identities) {
        sessions[identity.identity] = e2eSessions[identity.identity];
      }

      // Create independent browser contexts.
      for (const identity of identities) {
        const context = await browser.newContext();
        contexts.push(context);

        await context.addInitScript((session) => {
          window.localStorage.setItem('forge.auth.session', JSON.stringify(session));
        }, sessions[identity.identity]);

        pages[identity.identity] = await context.newPage();
      }

      const ownerPage = pages.owner;

      // Create a model as Owner.
      modelName = `FORGE Collaboration E2E ${Date.now()}`;

      await ownerPage.goto(`${BASE_URL}/workspace`);
      await ownerPage.locator('.create-dataModel-card').click();

      const createDialog = ownerPage.getByRole('dialog', {
        name: 'New Data Model',
      });

      await expect(createDialog).toBeVisible();
      await ownerPage.locator('#data-model-name').fill(modelName);
      await ownerPage.locator('#data-model-description').fill('Collaboration permission test');

      await createDialog.locator('button.save-button').click();

      await expect(ownerPage).toHaveURL(/\/workspace\/[^/]+\/model-studio$/, { timeout: 30_000 });

      await ownerPage.goto(`${BASE_URL}/workspace`);

      const ownerCard = ownerPage.locator('.dataModel-card').filter({
        has: ownerPage.getByRole('heading', {
          name: modelName,
          exact: true,
        }),
      });

      await expect(ownerCard).toHaveCount(1);

      await ownerCard
        .getByRole('button', {
          name: 'Share Data Model',
        })
        .click();

      const shareDialog = ownerPage.getByRole('dialog', {
        name: 'Share Data Model',
      });

      await expect(shareDialog).toBeVisible();

      const search = shareDialog.getByPlaceholder('Search by name or email');

      // Grant Contributor access.
      const contributor = identities.find((identity) => identity.identity === 'contributor')!;

      await search.fill(contributor.email);

      const contributorResult = shareDialog
        .locator('.user-search-result')
        .filter({ hasText: contributor.email });

      await expect(contributorResult).toBeVisible();
      await contributorResult.click();

      await shareDialog
        .getByRole('button', {
          name: 'Add Contributor',
        })
        .click();

      const contributorRecord = shareDialog
        .locator('.access-person')
        .filter({ hasText: contributor.email });

      await expect(contributorRecord).toContainText('Contributor');

      // Grant Viewer access.
      const viewer = identities.find((identity) => identity.identity === 'viewer')!;

      await search.fill(viewer.email);

      const viewerResult = shareDialog
        .locator('.user-search-result')
        .filter({ hasText: viewer.email });

      await expect(viewerResult).toBeVisible();
      await viewerResult.click();

      await shareDialog
        .locator('.role-option')
        .filter({
          hasText: 'Viewer',
        })
        .click();

      await shareDialog
        .getByRole('button', {
          name: 'Add Viewer',
        })
        .click();

      const viewerRecord = shareDialog.locator('.access-person').filter({ hasText: viewer.email });

      await expect(viewerRecord).toContainText('Viewer');
      await expect(shareDialog.locator('.access-person')).toHaveCount(3);

      await shareDialog
        .getByRole('button', {
          name: 'Done',
        })
        .click();

      // Verify Contributor and Viewer independently.
      for (const identity of [contributor, viewer]) {
        const page = pages[identity.identity];

        await page.goto(`${BASE_URL}/workspace`);

        const sharedCard = page.locator('.dataModel-card').filter({
          has: page.getByRole('heading', {
            name: modelName,
            exact: true,
          }),
        });

        await expect(sharedCard).toHaveCount(1);

        await expect(sharedCard).toContainText(
          identity.identity === 'contributor' ? 'Contributor' : 'Viewer',
        );

        await sharedCard
          .getByRole('button', {
            name: 'Share Data Model',
          })
          .click();

        const userShareDialog = page.getByRole('dialog', {
          name: 'Share Data Model',
        });

        await expect(userShareDialog).toBeVisible();
        await expect(userShareDialog).toContainText('Sharing is managed by the owner');

        await expect(userShareDialog.locator('.add-people-section')).toHaveCount(0);

        await expect(userShareDialog.getByRole('button', { name: 'Remove' })).toHaveCount(0);

        await expect(userShareDialog.locator('.access-role-option')).toHaveCount(0);
      }

      await attachPassScreenshot(testInfo, pages.owner, 'owner-sharing');
      await attachPassScreenshot(testInfo, pages.contributor, 'contributor-sharing');
      await attachPassScreenshot(testInfo, pages.viewer, 'viewer-sharing');
    } finally {
      // Close non-owner contexts before cleanup.
      for (const context of contexts.slice(1)) {
        await context.close();
      }

      // Delete only the model created by this test.
      if (modelName && pages.owner) {
        const ownerPage = pages.owner;

        await ownerPage.goto(`${BASE_URL}/workspace`);

        const card = ownerPage.locator('.dataModel-card').filter({
          has: ownerPage.getByRole('heading', {
            name: modelName,
            exact: true,
          }),
        });

        if ((await card.count()) === 1) {
          await card
            .getByRole('button', {
              name: 'Edit Data Model',
            })
            .click();

          const editDialog = ownerPage.getByRole('dialog', {
            name: 'Edit Data Model',
          });

          await expect(editDialog).toBeVisible();

          await editDialog.locator('button.delete-button').click();

          const confirmation = ownerPage.getByRole('dialog', {
            name: 'Delete this Data Model?',
          });

          await confirmation.locator('button.confirm-button').click();
          await expect(card).toHaveCount(0, { timeout: 30_000 });
        }
      }

      for (const context of contexts) {
        await context.close();
      }
    }
  });

  test('MU01-03: Owner changes roles and revokes Data Model access', async ({
    browser,
    request,
  }, testInfo) => {
    const e2eSessions = loadE2eSessions();
    const sessions: Record<string, any> = {};
    const contexts: BrowserContext[] = [];
    const pages: Record<string, import('@playwright/test').Page> = {};
    let modelName = '';

    try {
      // Bootstrap all three isolated identities.
      for (const identity of identities) {
        sessions[identity.identity] = e2eSessions[identity.identity];
      }

      // Create one browser context per identity.
      for (const identity of identities) {
        const context = await browser.newContext();
        contexts.push(context);

        await context.addInitScript((session) => {
          window.localStorage.setItem('forge.auth.session', JSON.stringify(session));
        }, sessions[identity.identity]);

        pages[identity.identity] = await context.newPage();
      }

      const ownerPage = pages.owner;
      const contributorPage = pages.contributor;
      const viewerPage = pages.viewer;

      const contributor = identities.find((identity) => identity.identity === 'contributor')!;

      const viewer = identities.find((identity) => identity.identity === 'viewer')!;

      // Owner creates a model.
      modelName = `FORGE Role Lifecycle E2E ${Date.now()}`;

      await ownerPage.goto(`${BASE_URL}/workspace`);
      await ownerPage.locator('.create-dataModel-card').click();

      const createDialog = ownerPage.getByRole('dialog', {
        name: 'New Data Model',
      });

      await expect(createDialog).toBeVisible();
      await ownerPage.locator('#data-model-name').fill(modelName);
      await ownerPage.locator('#data-model-description').fill('Role change and revocation test');

      await createDialog.locator('button.save-button').click();

      await expect(ownerPage).toHaveURL(/\/workspace\/[^/]+\/model-studio$/, { timeout: 30_000 });

      await ownerPage.goto(`${BASE_URL}/workspace`);

      const ownerCard = ownerPage.locator('.dataModel-card').filter({
        has: ownerPage.getByRole('heading', {
          name: modelName,
          exact: true,
        }),
      });

      await expect(ownerCard).toHaveCount(1);
      await ownerCard
        .getByRole('button', {
          name: 'Share Data Model',
        })
        .click();

      const shareDialog = ownerPage.getByRole('dialog', {
        name: 'Share Data Model',
      });

      await expect(shareDialog).toBeVisible();

      const search = shareDialog.getByPlaceholder('Search by name or email');

      // Grant Contributor access.
      await search.fill(contributor.email);

      const contributorResult = shareDialog
        .locator('.user-search-result')
        .filter({ hasText: contributor.email });

      await expect(contributorResult).toBeVisible();
      await contributorResult.click();

      await shareDialog
        .getByRole('button', {
          name: 'Add Contributor',
        })
        .click();

      const contributorRecord = shareDialog
        .locator('.access-person')
        .filter({ hasText: contributor.email });

      await expect(contributorRecord.locator('.access-role-option.selected')).toContainText(
        'Contributor',
      );

      // Grant Viewer access.
      await search.fill(viewer.email);

      const viewerResult = shareDialog
        .locator('.user-search-result')
        .filter({ hasText: viewer.email });

      await expect(viewerResult).toBeVisible();
      await viewerResult.click();

      await shareDialog
        .locator('.role-option')
        .filter({
          hasText: 'Viewer',
        })
        .click();

      await shareDialog
        .getByRole('button', {
          name: 'Add Viewer',
        })
        .click();

      const viewerRecord = shareDialog.locator('.access-person').filter({ hasText: viewer.email });

      await expect(viewerRecord.locator('.access-role-option.selected')).toContainText('Viewer');

      // Change Contributor to Viewer.
      await contributorRecord
        .locator('.access-role-option')
        .filter({
          hasText: 'Viewer',
        })
        .click();

      await expect(shareDialog.locator('.access-confirmation')).toContainText(
        'Change access level?',
      );

      await expect(shareDialog.locator('.access-confirmation')).toContainText(
        contributor.displayName,
      );

      await shareDialog
        .getByRole('button', {
          name: 'Change Access',
        })
        .click();

      await expect(contributorRecord.locator('.access-role-option.selected')).toContainText(
        'Viewer',
      );

      // Verify the changed role from the Contributor identity.
      await contributorPage.goto(`${BASE_URL}/workspace`);

      const contributorCard = contributorPage.locator('.dataModel-card').filter({
        has: contributorPage.getByRole('heading', {
          name: modelName,
          exact: true,
        }),
      });

      await expect(contributorCard).toHaveCount(1);
      await expect(contributorCard).toContainText('Viewer');

      // Change the same user back to Contributor.
      await contributorRecord
        .locator('.access-role-option')
        .filter({
          hasText: 'Contributor',
        })
        .click();

      await expect(shareDialog.locator('.access-confirmation')).toContainText(
        'Change access level?',
      );

      await shareDialog
        .getByRole('button', {
          name: 'Change Access',
        })
        .click();

      await expect(contributorRecord.locator('.access-role-option.selected')).toContainText(
        'Contributor',
      );

      await contributorPage.reload();

      await expect(contributorCard).toContainText('Contributor');

      // Revoke the original Viewer's access.
      await viewerRecord
        .getByRole('button', {
          name: 'Remove',
        })
        .click();

      await expect(shareDialog.locator('.access-confirmation')).toContainText('Remove access?');

      await expect(shareDialog.locator('.access-confirmation')).toContainText(viewer.displayName);

      await shareDialog
        .getByRole('button', {
          name: 'Remove Access',
        })
        .click();

      await expect(
        shareDialog.locator('.access-person').filter({
          hasText: viewer.email,
        }),
      ).toHaveCount(0);

      // Verify the revoked Viewer no longer sees the model.
      await viewerPage.goto(`${BASE_URL}/workspace`);

      const revokedCard = viewerPage.locator('.dataModel-card').filter({
        has: viewerPage.getByRole('heading', {
          name: modelName,
          exact: true,
        }),
      });

      await expect(revokedCard).toHaveCount(0);

      // Contributor retains access.
      await contributorPage.reload();
      await expect(contributorCard).toHaveCount(1);
      await expect(contributorCard).toContainText('Contributor');

      await attachPassScreenshot(testInfo, pages.owner, 'owner-role-lifecycle');
      await attachPassScreenshot(testInfo, pages.contributor, 'contributor-role-lifecycle');
      await attachPassScreenshot(testInfo, pages.viewer, 'viewer-role-revoked');
    } finally {
      // Close non-owner sessions before model cleanup.
      for (const context of contexts.slice(1)) {
        await context.close();
      }

      // Delete only the model created by this test.
      if (modelName && pages.owner) {
        const ownerPage = pages.owner;

        await ownerPage.goto(`${BASE_URL}/workspace`);

        const card = ownerPage.locator('.dataModel-card').filter({
          has: ownerPage.getByRole('heading', {
            name: modelName,
            exact: true,
          }),
        });

        if ((await card.count()) === 1) {
          await card
            .getByRole('button', {
              name: 'Edit Data Model',
            })
            .click();

          const editDialog = ownerPage.getByRole('dialog', {
            name: 'Edit Data Model',
          });

          await expect(editDialog).toBeVisible();
          await editDialog.locator('button.delete-button').click();

          const confirmation = ownerPage.getByRole('dialog', {
            name: 'Delete this Data Model?',
          });

          await confirmation.locator('button.confirm-button').click();
          await expect(card).toHaveCount(0, { timeout: 30_000 });
        }
      }

      for (const context of contexts) {
        await context.close();
      }
    }
  });
});
