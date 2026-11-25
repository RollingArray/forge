import { test, expect } from './workspace.fixtures';

test.describe('WS02 - Workspace Data Models', () => {
  test('WS02-01: displays a newly created model with its details', async ({
    page,
    workspaceModel,
  }) => {
    const card = page.locator('.dataModel-card').filter({
      has: page.getByRole('heading', {
        name: workspaceModel.name,
        exact: true,
      }),
    });

    await expect(card).toHaveCount(1);
    await expect(card).toContainText(workspaceModel.description);
    await expect(card).toContainText('0 entities');
    await expect(card).toContainText('0 relationships');
    await expect(card).toContainText('Owner');
    await expect(card).toContainText('Draft');
  });

  test('WS02-02: selecting a model card opens Model Studio', async ({
    page,
    workspaceModel,
  }) => {
    await workspaceModel.card.click();

    await expect(page).toHaveURL(
      /\/workspace\/[^/]+\/model-studio$/,
    );

    await expect(page.locator('app-model-studio')).toBeVisible();
  });

  test('WS02-03: model card supports keyboard selection with Enter', async ({
    page,
    workspaceModel,
  }) => {
    await workspaceModel.card.focus();
    await workspaceModel.card.press('Enter');

    await expect(page).toHaveURL(
      /\/workspace\/[^/]+\/model-studio$/,
    );
  });

  test('WS02-04: model card supports keyboard selection with Space', async ({
    page,
    workspaceModel,
  }) => {
    await workspaceModel.card.focus();
    await workspaceModel.card.press('Space');

    await expect(page).toHaveURL(
      /\/workspace\/[^/]+\/model-studio$/,
    );
  });

  test('WS02-05: Edit action opens the edit dialog without selecting the card', async ({
    page,
    workspaceModel,
  }) => {
    await workspaceModel.card.getByRole('button', {
      name: 'Data Model actions',
    }).click();

    await workspaceModel.card.getByRole('menuitem', {
      name: 'Edit',
    }).click();

    await expect(page).toHaveURL(/\/workspace\/?$/);

    await expect(
      page.getByRole('dialog', {
        name: 'Edit Data Model',
      }),
    ).toBeVisible();

    await expect(
      page.locator('#data-model-name'),
    ).toHaveValue(workspaceModel.name);
  });


  test('WS02-06: duplicates a data model while preserving the original', async ({
    page,
    workspaceModel,
  }) => {
    let duplicateName: string | null = null;
    let duplicateId: string | null = null;
    let duplicateRequests = 0;

    const duplicateEndpoint = /\/data-models\/[^/]+\/duplicate$/;

    page.on('request', (request) => {
      if (
        request.method() === 'POST' &&
        duplicateEndpoint.test(new URL(request.url()).pathname)
      ) {
        duplicateRequests += 1;
      }
    });

    try {
      const originalCard = page.locator('.dataModel-card').filter({
        has: page.getByRole('heading', {
          name: workspaceModel.name,
          exact: true,
        }),
      });

      await expect(originalCard).toHaveCount(1);

      // Open the card actions and inspect the confirmation.
      await originalCard.getByRole('button', {
        name: 'Data Model actions',
      }).click();

      await originalCard.getByRole('menuitem', {
        name: 'Duplicate',
      }).click();

      const confirmation = page.getByRole('dialog', {
        name: 'Duplicate this Data Model?',
      });

      await expect(confirmation).toBeVisible();
      await expect(confirmation).toContainText(workspaceModel.name);
      await expect(confirmation).toContainText('Included:');
      await expect(confirmation).toContainText('complete specification');
      await expect(confirmation).toContainText('entities');
      await expect(confirmation).toContainText('relationships');
      await expect(confirmation).toContainText('constraints');
      await expect(confirmation).toContainText('Excluded:');
      await expect(confirmation).toContainText('generated datasets');
      await expect(confirmation).toContainText('generation jobs');
      await expect(confirmation).toContainText('checkpoints');
      await expect(confirmation).toContainText('execution history');

      // Cancellation must not send a duplication request.
      await confirmation.locator('button.cancel-button').click();

      await expect(confirmation).toHaveCount(0);
      expect(duplicateRequests).toBe(0);

      await expect(originalCard).toHaveCount(1);

      // Reopen the confirmation and explicitly approve duplication.
      await originalCard.getByRole('button', {
        name: 'Data Model actions',
      }).click();

      await originalCard.getByRole('menuitem', {
        name: 'Duplicate',
      }).click();

      const secondConfirmation = page.getByRole('dialog', {
        name: 'Duplicate this Data Model?',
      });

      await expect(secondConfirmation).toBeVisible();

      const responsePromise = page.waitForResponse((response) =>
        response.request().method() === 'POST' &&
        duplicateEndpoint.test(new URL(response.url()).pathname),
      );

      await secondConfirmation.locator('button.confirm-button').click();

      const response = await responsePromise;

      expect(response.status()).toBe(201);
      expect(duplicateRequests).toBe(1);

      const result = await response.json() as {
        data_model_id: string;
        name: string;
      };

      duplicateId = result.data_model_id;
      duplicateName = result.name;

      expect(duplicateId).toBeTruthy();
      const sourceModelId = new URL(response.url())
        .pathname
        .match(/\/data-models\/([^/]+)\/duplicate$/)?.[1];

      expect(sourceModelId).toBeTruthy();
      expect(duplicateId).not.toBe(sourceModelId);
      expect(duplicateName).toBe(
        `Copy of ${workspaceModel.name} - ${sourceModelId}`,
      );

      await expect(secondConfirmation).toHaveCount(0);

      // Successful duplication opens the new model in Model Studio.
      await expect(page).toHaveURL(
        new RegExp(`/workspace/${duplicateId}/model-studio$`),
        { timeout: 30_000 },
      );

      await expect(page.locator('app-model-studio')).toBeVisible();

      // Verify that both models exist independently in the workspace.
      await page.goto('/workspace');

      const originalAfterDuplication = page.locator('.dataModel-card').filter({
        has: page.getByRole('heading', {
          name: workspaceModel.name,
          exact: true,
        }),
      });

      const duplicateCard = page.locator('.dataModel-card').filter({
        has: page.getByRole('heading', {
          name: duplicateName,
          exact: true,
        }),
      });

      await expect(originalAfterDuplication).toHaveCount(1);
      await expect(originalAfterDuplication).toContainText(
        workspaceModel.description,
      );
      await expect(duplicateCard).toHaveCount(1);
      await expect(duplicateCard).toContainText(
        workspaceModel.description,
      );
    } finally {
      // Remove only the duplicate created by this test.
      // The workspace fixture independently cleans up the original.
      if (duplicateName) {
        try {
          await page.goto('/workspace');

          const duplicateCard = page.locator('.dataModel-card').filter({
            has: page.getByRole('heading', {
              name: duplicateName,
              exact: true,
            }),
          });

          await expect(duplicateCard).toHaveCount(1);

          await duplicateCard.getByRole('button', {
            name: 'Data Model actions',
          }).click();

          await duplicateCard.getByRole('menuitem', {
            name: 'Edit',
          }).click();

          const editDialog = page.getByRole('dialog', {
            name: 'Edit Data Model',
          });

          await expect(editDialog).toBeVisible();
          await editDialog.locator('button.delete-button').click();

          const deleteConfirmation = page.getByRole('dialog', {
            name: 'Delete this Data Model?',
          });

          await expect(deleteConfirmation).toBeVisible();
          await deleteConfirmation.locator('button.confirm-button').click();

          await expect(duplicateCard).toHaveCount(0, {
            timeout: 30_000,
          });
        } catch (cleanupError) {
          console.warn(
            `Could not automatically clean up duplicate ${duplicateId ?? duplicateName}:`,
            cleanupError,
          );
        }
      }
    }
  });
});
