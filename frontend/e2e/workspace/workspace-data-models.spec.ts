import { test, expect } from './workspace.fixtures';

test.describe('Workspace data models', () => {
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
      name: 'Edit Data Model',
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
});
