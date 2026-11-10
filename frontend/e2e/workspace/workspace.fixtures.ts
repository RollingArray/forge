import { test as base, expect, Page, Locator } from '@playwright/test';

export interface WorkspaceTestModel {
  name: string;
  description: string;
  card: Locator;
  deletedByTest: boolean;
}

async function findUniqueModelCard(
  page: Page,
  modelName: string,
): Promise<Locator> {
  const card = page.locator('.dataModel-card').filter({
    has: page.getByRole('heading', {
      name: modelName,
      exact: true,
    }),
  });

  await expect(
    card,
    `Expected exactly one test-owned model card: ${modelName}`,
  ).toHaveCount(1);

  return card;
}

async function createWorkspaceModel(
  page: Page,
): Promise<WorkspaceTestModel> {
  const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const name = `FORGE WS E2E ${uniqueId}`;
  const description = `Workspace E2E test model ${uniqueId}`;

  await page.goto('/workspace');
  await expect(page.locator('app-workspace')).toBeVisible();

  await page.locator('.create-dataModel-card').click();

  const dialog = page.getByRole('dialog', {
    name: 'New Data Model',
  });

  await expect(dialog).toBeVisible();
  await page.locator('#data-model-name').fill(name);
  await page.locator('#data-model-description').fill(description);

  const saveButton = dialog.locator('button.save-button');
  await expect(saveButton).toBeVisible();
  await expect(saveButton).toBeEnabled();
  await saveButton.click();

  await expect(page).toHaveURL(
    /\/workspace\/[^/]+\/model-studio$/,
    { timeout: 30_000 },
  );

  await page.goto('/workspace');

  const card = await findUniqueModelCard(page, name);
  await expect(card).toContainText(description);

  return { name, description, card, deletedByTest: false };
}

async function deleteWorkspaceModel(
  page: Page,
  modelName: string,
): Promise<void> {
  await page.goto('/workspace');
  await expect(page.locator('app-workspace')).toBeVisible();

  // Safety check: never delete unless exactly one matching model exists.
  const card = await findUniqueModelCard(page, modelName);

  await card.getByRole('button', {
    name: 'Edit Data Model',
  }).click();

  const editDialog = page.getByRole('dialog', {
    name: 'Edit Data Model',
  });

  await expect(editDialog).toBeVisible();

  await editDialog.locator('button.delete-button').click();

  const confirmation = page.getByRole('dialog', {
    name: 'Delete this Data Model?',
  });

  await expect(confirmation).toBeVisible();
  await expect(confirmation).toContainText(modelName);

  const confirmDeleteButton = confirmation.locator('button.confirm-button');
  await expect(confirmDeleteButton).toBeVisible();
  await expect(confirmDeleteButton).toBeEnabled();
  await confirmDeleteButton.click();

  await expect(
    page.locator('.dataModel-card').filter({
      has: page.getByRole('heading', {
        name: modelName,
        exact: true,
      }),
    }),
  ).toHaveCount(0, { timeout: 30_000 });
}

export const test = base.extend<{
  workspaceModel: WorkspaceTestModel;
}>({
  workspaceModel: async ({ page }, use) => {
    const model = await createWorkspaceModel(page);

    try {
      await use(model);
    } finally {
      if (!model.deletedByTest) {
        await deleteWorkspaceModel(page, model.name);
      }
    }
  },
});

export { expect };
