import { test, expect } from './model-studio.fixtures';

test.describe('MS07 - Field deletion', () => {
  test.describe.configure({ timeout: 120_000 });

  async function openExistingField(
    page: import('@playwright/test').Page,
    entityName: string,
    fieldName: string,
  ) {
    const entityNode = page.locator('app-model-studio-entity-node')
      .filter({ hasText: entityName });

    await expect(entityNode).toHaveCount(1);
    await entityNode.click();

    const inspector = page.locator('app-model-studio-entity-inspector');

    await inspector.getByRole('button', {
      name: 'Fields',
      exact: true,
    }).click();

    const fieldRow = inspector.locator('app-inspector-row')
      .filter({ hasText: fieldName });

    await expect(fieldRow).toHaveCount(1);
    await fieldRow.locator('button.inspector-row-edit').click();

    const editDialog = page.getByRole('dialog', {
      name: 'Edit Field',
      exact: true,
    });

    await expect(editDialog).toBeVisible();

    return { inspector, fieldRow, editDialog };
  }

  async function requestDeletion(
    page: import('@playwright/test').Page,
    editDialog: import('@playwright/test').Locator,
    entityName: string,
    fieldName: string,
  ) {
    await editDialog.locator('.delete-field-button').click();

    const confirmation = page.getByRole('dialog', {
      name: 'Delete this Field?',
      exact: true,
    });

    await expect(confirmation).toBeVisible();
    await expect(confirmation).toContainText(
      `${entityName}.${fieldName}`,
    );

    return confirmation;
  }

  function fieldDeletePath(
    modelId: string,
    entityName: string,
    fieldName: string,
  ) {
    return new RegExp(
      `/data-models/${modelId}/specification/entities/` +
      `${encodeURIComponent(entityName)}/fields/` +
      `${encodeURIComponent(fieldName)}$`,
    );
  }

  async function confirmDeletion(
    page: import('@playwright/test').Page,
    confirmation: import('@playwright/test').Locator,
    deletePath: RegExp,
  ) {
    const responsePromise = page.waitForResponse((response) =>
      response.request().method() === 'DELETE' &&
      deletePath.test(new URL(response.url()).pathname),
    );

    await confirmation.getByRole('button', {
      name: 'Delete Field',
      exact: true,
    }).click();

    return responsePromise;
  }

  test('MS07-01: Request field deletion and display confirmation', async ({
    page,
    populatedModelStudio,
  }) => {
    const { editDialog } = await openExistingField(
      page,
      'Customer',
      'CUSTOMER_NAME',
    );

    const confirmation = await requestDeletion(
      page,
      editDialog,
      'Customer',
      'CUSTOMER_NAME',
    );

    await expect(confirmation.getByRole('button', {
      name: 'Delete Field',
      exact: true,
    })).toBeVisible();

    await expect(confirmation).toContainText(
      'Fields used by an identity, relationship, foreign key, or constraint cannot be deleted.',
    );
  });

  test('MS07-02: Cancel field deletion', async ({
    page,
    populatedModelStudio,
  }) => {
    const { fieldRow, editDialog } = await openExistingField(
      page,
      'Customer',
      'CUSTOMER_NAME',
    );

    let deleteRequests = 0;
    const deletePath = fieldDeletePath(
      populatedModelStudio.id,
      'Customer',
      'CUSTOMER_NAME',
    );

    await page.route(deletePath, async (route) => {
      deleteRequests += 1;
      await route.continue();
    });

    const confirmation = await requestDeletion(
      page,
      editDialog,
      'Customer',
      'CUSTOMER_NAME',
    );

    await confirmation.locator(
      '.confirmation-button.cancel-button',
    ).click();

    await expect(confirmation).toBeHidden();
    await expect(editDialog).toBeVisible();
    await expect(fieldRow).toHaveCount(1);
    expect(deleteRequests).toBe(0);

    await page.unroute(deletePath);
  });

  test('MS07-03: Delete a field without dependencies', async ({
    page,
    populatedModelStudio,
  }) => {
    const { inspector, fieldRow, editDialog } = await openExistingField(
      page,
      'Customer',
      'CUSTOMER_NAME',
    );

    const confirmation = await requestDeletion(
      page,
      editDialog,
      'Customer',
      'CUSTOMER_NAME',
    );

    const deleteResponse = await confirmDeletion(
      page,
      confirmation,
      fieldDeletePath(
        populatedModelStudio.id,
        'Customer',
        'CUSTOMER_NAME',
      ),
    );

    expect(deleteResponse.status()).toBe(204);

    await expect(editDialog).toBeHidden();
    await expect(fieldRow).toHaveCount(0);
    await expect(
      inspector.getByText('CUSTOMER_NAME', { exact: true }),
    ).toHaveCount(0);
  });

  test('MS07-04: Block deletion of a field used by entity identity', async ({
    page,
    populatedModelStudio,
  }) => {
    const { fieldRow, editDialog } = await openExistingField(
      page,
      'Customer',
      'CUSTOMER_ID',
    );

    const confirmation = await requestDeletion(
      page,
      editDialog,
      'Customer',
      'CUSTOMER_ID',
    );

    const deleteResponse = await confirmDeletion(
      page,
      confirmation,
      fieldDeletePath(
        populatedModelStudio.id,
        'Customer',
        'CUSTOMER_ID',
      ),
    );

    expect(deleteResponse.status()).toBe(409);

    await expect(confirmation.locator('[role="alert"]'))
      .toContainText('part of the entity identity');

    await expect(editDialog).toBeVisible();
    await expect(fieldRow).toHaveCount(1);
  });

  test('MS07-05: Block deletion of a field used by a foreign key', async ({
    page,
    populatedModelStudio,
  }) => {
    const { fieldRow, editDialog } = await openExistingField(
      page,
      'Order',
      'CUSTOMER_ID',
    );

    const confirmation = await requestDeletion(
      page,
      editDialog,
      'Order',
      'CUSTOMER_ID',
    );

    const deleteResponse = await confirmDeletion(
      page,
      confirmation,
      fieldDeletePath(
        populatedModelStudio.id,
        'Order',
        'CUSTOMER_ID',
      ),
    );

    expect(deleteResponse.status()).toBe(409);

    await expect(confirmation.locator('[role="alert"]'))
      .toContainText('used by foreign key');

    await expect(editDialog).toBeVisible();
    await expect(fieldRow).toHaveCount(1);
  });

  test('MS07-06: Display deletion failure and allow retry', async ({
    page,
    populatedModelStudio,
  }) => {
    const entityName = 'Customer';
    const fieldName = 'CUSTOMER_NAME';
    const deletePath = fieldDeletePath(
      populatedModelStudio.id,
      entityName,
      fieldName,
    );

    const { fieldRow, editDialog } = await openExistingField(
      page,
      entityName,
      fieldName,
    );

    const confirmation = await requestDeletion(
      page,
      editDialog,
      entityName,
      fieldName,
    );

    let failedFirstAttempt = false;

    await page.route(deletePath, async (route) => {
      if (!failedFirstAttempt) {
        failedFirstAttempt = true;
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Simulated field deletion failure',
          }),
        });
        return;
      }

      await route.continue();
    });

    const firstResponse = await confirmDeletion(
      page,
      confirmation,
      deletePath,
    );

    expect(firstResponse.status()).toBe(500);

    await expect(confirmation.locator('[role="alert"]'))
      .toContainText('Simulated field deletion failure');

    await expect(editDialog).toBeVisible();
    await expect(fieldRow).toHaveCount(1);

    const retryResponse = await confirmDeletion(
      page,
      confirmation,
      deletePath,
    );

    expect(retryResponse.status()).toBe(204);

    await expect(editDialog).toBeHidden();
    await expect(fieldRow).toHaveCount(0);

    await page.unroute(deletePath);
  });
});
