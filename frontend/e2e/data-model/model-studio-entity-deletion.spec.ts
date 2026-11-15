import { test, expect } from './model-studio.fixtures';

test.describe('MS04 - Entity deletion', () => {
  test.describe.configure({ timeout: 120_000 });

  async function createEntity(
    page: import('@playwright/test').Page,
    modelId: string,
    entityName: string,
  ) {
    await page.locator('app-specification-entry-panel')
      .getByRole('button', { name: /Add Entity/ }).click();

    const dialog = page.getByRole('dialog', {
      name: 'Add Entity',
      exact: true,
    });

    await dialog.locator('#entity-name').fill(entityName);
    await dialog.locator('#entity-description').fill(
      `Entity deletion test ${entityName}`,
    );

    const responsePromise = page.waitForResponse((response) => {
      const request = response.request();
      return request.method() === 'POST' &&
        new URL(response.url()).pathname.endsWith(
          `/data-models/${modelId}/specification/entities`,
        );
    });

    await dialog.getByRole('button', {
      name: 'Add Entity',
      exact: true,
    }).click();

    const response = await responsePromise;
    expect(response.status()).toBe(201);
    await expect(dialog).toBeHidden();
  }

  async function openEntityForEditing(
    page: import('@playwright/test').Page,
    entityName: string,
  ) {
    const entityNode = page.locator('app-model-studio-entity-node')
      .filter({ hasText: entityName });

    await expect(entityNode).toHaveCount(1);
    await entityNode.click();

    const inspector = page.locator('app-model-studio-entity-inspector');
    await inspector.locator('.edit-button').click();

    const editDialog = page.getByRole('dialog', {
      name: 'Edit Entity',
      exact: true,
    });

    await expect(editDialog).toBeVisible();
    return { entityNode, editDialog };
  }

  async function requestDeletion(
    editDialog: import('@playwright/test').Locator,
  ) {
    await editDialog.locator('.delete-entity-button').click();

    const confirmation = editDialog.page().getByRole('dialog', {
      name: 'Delete this Entity?',
      exact: true,
    });

    await expect(confirmation).toBeVisible();
    return confirmation;
  }

  test('MS04-01: Request entity deletion', async ({
    page,
    modelStudio,
  }) => {
    const entityName = `E2E Delete Request ${Date.now()}`;

    await createEntity(page, modelStudio.id, entityName);
    const { editDialog } = await openEntityForEditing(page, entityName);
    const confirmation = await requestDeletion(editDialog);

    await expect(confirmation.getByText(entityName, {
      exact: true,
    })).toBeVisible();

    await expect(confirmation.getByRole('button', {
      name: 'Delete Entity',
      exact: true,
    })).toBeVisible();
  });

  test('MS04-02: Cancel deletion', async ({
    page,
    modelStudio,
  }) => {
    const entityName = `E2E Delete Cancel ${Date.now()}`;

    await createEntity(page, modelStudio.id, entityName);
    const { entityNode, editDialog } = await openEntityForEditing(
      page,
      entityName,
    );

    const confirmation = await requestDeletion(editDialog);

    await confirmation.locator('.confirmation-button.cancel-button').click();

    await expect(confirmation).toBeHidden();
    await expect(editDialog).toBeVisible();
    await expect(entityNode).toHaveCount(1);
  });

  test('MS04-03: Confirm deletion of an eligible entity', async ({
    page,
    modelStudio,
  }) => {
    const entityName = `E2E Delete Eligible ${Date.now()}`;

    await createEntity(page, modelStudio.id, entityName);
    const { entityNode, editDialog } = await openEntityForEditing(
      page,
      entityName,
    );

    const confirmation = await requestDeletion(editDialog);

    const deleteResponsePromise = page.waitForResponse((response) => {
      const request = response.request();
      const pathname = new URL(response.url()).pathname;

      return request.method() === 'DELETE' &&
        pathname.endsWith(
          `/data-models/${modelStudio.id}/specification/entities/${encodeURIComponent(entityName)}`,
        );
    });

    await confirmation.getByRole('button', {
      name: 'Delete Entity',
      exact: true,
    }).click();

    const deleteResponse = await deleteResponsePromise;
    expect(deleteResponse.status()).toBe(204);

    await expect(editDialog).toBeHidden();
    await expect(entityNode).toHaveCount(0);
  });

  test('MS04-04: Attempt deletion with dependent fields or model structures', async ({
    page,
    populatedModelStudio,
  }) => {
    const entityName = 'Customer';

    const { entityNode, editDialog } = await openEntityForEditing(
      page,
      entityName,
    );

    const confirmation = await requestDeletion(editDialog);

    const deleteResponsePromise = page.waitForResponse((response) => {
      const request = response.request();
      const pathname = new URL(response.url()).pathname;

      return request.method() === 'DELETE' &&
        pathname.endsWith(
          `/data-models/${populatedModelStudio.id}/specification/entities/${encodeURIComponent(entityName)}`,
        );
    });

    await confirmation.getByRole('button', {
      name: 'Delete Entity',
      exact: true,
    }).click();

    const deleteResponse = await deleteResponsePromise;
    expect(deleteResponse.status()).toBe(409);

    await expect(confirmation.locator('[role="alert"]')).toBeVisible();
    await expect(editDialog).toBeVisible();
    await expect(entityNode).toHaveCount(1);
  });

  test('MS04-05: Simulate deletion API failure', async ({
    page,
    modelStudio,
  }) => {
    const entityName = `E2E Delete Failure ${Date.now()}`;
    const deletePath = new RegExp(
      `/data-models/${modelStudio.id}/specification/entities/${encodeURIComponent(entityName)}$`,
    );

    await createEntity(page, modelStudio.id, entityName);
    const { entityNode, editDialog } = await openEntityForEditing(
      page,
      entityName,
    );

    const confirmation = await requestDeletion(editDialog);

    await page.route(deletePath, async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Simulated deletion failure',
        }),
      });
    });

    const deleteResponsePromise = page.waitForResponse((response) =>
      response.request().method() === 'DELETE' &&
      deletePath.test(new URL(response.url()).pathname),
    );

    await confirmation.getByRole('button', {
      name: 'Delete Entity',
      exact: true,
    }).click();

    const deleteResponse = await deleteResponsePromise;
    expect(deleteResponse.status()).toBe(500);

    await expect(confirmation.locator('[role="alert"]')).toContainText(
      'Simulated deletion failure',
    );
    await expect(editDialog).toBeVisible();
    await expect(entityNode).toHaveCount(1);

    await page.unroute(deletePath);
  });

  test('MS04-06: Retry deletion after failure', async ({
    page,
    modelStudio,
  }) => {
    const entityName = `E2E Delete Retry ${Date.now()}`;
    const deletePath = new RegExp(
      `/data-models/${modelStudio.id}/specification/entities/${encodeURIComponent(entityName)}$`,
    );

    await createEntity(page, modelStudio.id, entityName);
    const { entityNode, editDialog } = await openEntityForEditing(
      page,
      entityName,
    );

    const confirmation = await requestDeletion(editDialog);
    let failedFirstAttempt = false;

    await page.route(deletePath, async (route) => {
      if (!failedFirstAttempt) {
        failedFirstAttempt = true;
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Simulated first-attempt failure',
          }),
        });
        return;
      }

      await route.continue();
    });

    const firstResponsePromise = page.waitForResponse((response) =>
      response.request().method() === 'DELETE' &&
      deletePath.test(new URL(response.url()).pathname),
    );

    await confirmation.getByRole('button', {
      name: 'Delete Entity',
      exact: true,
    }).click();

    const firstResponse = await firstResponsePromise;
    expect(firstResponse.status()).toBe(500);

    await expect(confirmation.locator('[role="alert"]')).toBeVisible();
    await expect(entityNode).toHaveCount(1);

    const retryResponsePromise = page.waitForResponse((response) =>
      response.request().method() === 'DELETE' &&
      deletePath.test(new URL(response.url()).pathname),
    );

    await confirmation.getByRole('button', {
      name: 'Delete Entity',
      exact: true,
    }).click();

    const retryResponse = await retryResponsePromise;
    expect(retryResponse.status()).toBe(204);

    await expect(editDialog).toBeHidden();
    await expect(entityNode).toHaveCount(0);

    await page.unroute(deletePath);
  });
});
