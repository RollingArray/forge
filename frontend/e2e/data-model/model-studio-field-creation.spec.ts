import { test, expect } from './model-studio.fixtures';

test.describe('MS05 - Field creation', () => {
  test.describe.configure({ timeout: 120_000 });

  async function openFieldDialog(
    page: import('@playwright/test').Page,
    entityName = 'Customer',
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

    const addFieldButton = inspector.locator(
      'app-inspector-fields .inspector-action, app-inspector-fields .empty-action',
    );

    await expect(addFieldButton).toBeVisible();
    await addFieldButton.click();

    const dialog = page.getByRole('dialog', {
      name: 'Add Field',
      exact: true,
    });

    await expect(dialog).toBeVisible();

    return { entityNode, inspector, dialog };
  }

  async function selectIdentifierType(
    dialog: import('@playwright/test').Locator,
  ) {
    await dialog.getByText('Unique ID', { exact: true }).click();

    await expect(
      dialog.getByText('Sequential IDs', { exact: true }),
    ).toBeVisible();
  }

  function fieldCreationPath(modelId: string, entityName = 'Customer') {
    return `/data-models/${modelId}/specification/entities/${encodeURIComponent(entityName)}/fields`;
  }

  test('MS05-01: Open field creation dialog', async ({
    page,
    populatedModelStudio,
  }) => {
    await expect(page).toHaveURL(
      new RegExp(`/workspace/${populatedModelStudio.id}/model-studio$`),
    );

    const { dialog } = await openFieldDialog(page);

    await expect(dialog.locator('#field-name')).toBeVisible();

    await expect(
      dialog.locator('.save-button'),
    ).toBeVisible();

    await expect(
      dialog.locator('.cancel-button'),
    ).toBeVisible();
  });

  test('MS05-02: Create a valid field', async ({
    page,
    populatedModelStudio,
  }) => {
    const fieldName = `E2E_FIELD_${Date.now()}`;

    const { inspector, dialog } = await openFieldDialog(page);

    await dialog.locator('#field-name').fill(fieldName);
    await selectIdentifierType(dialog);

    const saveButton = dialog.locator('.save-button');

    await expect(saveButton).toBeEnabled();

    const createResponsePromise = page.waitForResponse((response) => {
      const request = response.request();
      const pathname = new URL(response.url()).pathname;

      return (
        request.method() === 'POST' &&
        pathname.endsWith(fieldCreationPath(populatedModelStudio.id))
      );
    });

    await saveButton.click();

    const createResponse = await createResponsePromise;
    const responseBody = await createResponse.text();

    expect(
      createResponse.status(),
      `Field creation should return HTTP 201. API response: ${responseBody}`,
    ).toBe(201);

    const createdField = JSON.parse(responseBody);

    expect(createdField.name).toBe(fieldName);
    expect(createdField.type).toBe('IDENTIFIER');
    expect(createdField.identity).toEqual({
      strategy: 'SEQUENTIAL_ID',
    });

    await expect(dialog).toBeHidden();

    await expect(
      inspector.locator('.field-card-name').filter({
        hasText: fieldName,
      }),
    ).toHaveCount(1);
  });

  test('MS05-03: Create field with empty name', async ({
    page,
    populatedModelStudio,
  }) => {
    const { dialog, inspector } = await openFieldDialog(page);

    await selectIdentifierType(dialog);

    const nameInput = dialog.locator('#field-name');

    await expect(nameInput).toHaveValue('');

    const saveButton = dialog.locator('.save-button');

    await expect(saveButton).toBeDisabled();
    await expect(dialog).toBeVisible();

    await expect(
      inspector.locator('.field-card-name'),
    ).toHaveCount(2);

    // The disabled Save action must not issue a field-creation request.
    let createRequests = 0;
    const fieldPath = fieldCreationPath(populatedModelStudio.id);

    await page.route('**/fields', async (route) => {
      const request = route.request();
      const pathname = new URL(request.url()).pathname;

      if (
        request.method() === 'POST' &&
        pathname.endsWith(fieldPath)
      ) {
        createRequests += 1;
      }

      await route.continue();
    });

    await expect(saveButton).toBeDisabled();
    expect(createRequests).toBe(0);
  });

  test('MS05-04: Create duplicate field name', async ({
    page,
    populatedModelStudio,
  }) => {
    const { dialog, inspector } = await openFieldDialog(page);

    await dialog.locator('#field-name').fill('CUSTOMER_ID');
    await selectIdentifierType(dialog);

    const saveButton = dialog.locator('.save-button');

    await expect(saveButton).toBeEnabled();

    const createResponsePromise = page.waitForResponse((response) => {
      const request = response.request();
      const pathname = new URL(response.url()).pathname;

      return (
        request.method() === 'POST' &&
        pathname.endsWith(fieldCreationPath(populatedModelStudio.id))
      );
    });

    await saveButton.click();

    const createResponse = await createResponsePromise;

    expect(
      createResponse.status(),
      'Duplicate field creation should return HTTP 409',
    ).toBe(409);

    // The rejected operation must leave the dialog and existing field intact.
    await expect(dialog).toBeVisible();

    await expect(
      inspector.locator('.field-card-name').getByText('CUSTOMER_ID', {
        exact: true,
      }),
    ).toHaveCount(1);
  });

  test('MS05-05: Cancel field creation', async ({
    page,
    populatedModelStudio,
  }) => {
    const fieldName = `E2E_CANCEL_FIELD_${Date.now()}`;

    const { dialog, inspector } = await openFieldDialog(page);

    await dialog.locator('#field-name').fill(fieldName);
    await selectIdentifierType(dialog);

    await expect(
      dialog.locator('.save-button'),
    ).toBeEnabled();

    let createRequests = 0;
    const fieldPath = fieldCreationPath(populatedModelStudio.id);

    await page.route('**/fields', async (route) => {
      const request = route.request();
      const pathname = new URL(request.url()).pathname;

      if (
        request.method() === 'POST' &&
        pathname.endsWith(fieldPath)
      ) {
        createRequests += 1;
      }

      await route.continue();
    });

    await dialog.locator('.cancel-button').click();

    await expect(dialog).toBeHidden();

    expect(
      createRequests,
      'Cancelling should not issue a field-creation request',
    ).toBe(0);

    await expect(
      inspector.locator('.field-card-name').filter({
        hasText: fieldName,
      }),
    ).toHaveCount(0);
  });

  test('MS05-06: Reload after creation', async ({
    page,
    populatedModelStudio,
  }) => {
    const fieldName = `E2E_RELOAD_FIELD_${Date.now()}`;

    const { dialog } = await openFieldDialog(page);

    await dialog.locator('#field-name').fill(fieldName);
    await selectIdentifierType(dialog);

    const createResponsePromise = page.waitForResponse((response) => {
      const request = response.request();
      const pathname = new URL(response.url()).pathname;

      return (
        request.method() === 'POST' &&
        pathname.endsWith(fieldCreationPath(populatedModelStudio.id))
      );
    });

    await dialog.locator('.save-button').click();

    const createResponse = await createResponsePromise;
    const responseBody = await createResponse.text();

    expect(
      createResponse.status(),
      `Field creation should return HTTP 201. API response: ${responseBody}`,
    ).toBe(201);

    await expect(dialog).toBeHidden();

    await page.reload();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${populatedModelStudio.id}/model-studio$`),
    );

    await expect(
      page.getByRole('heading', {
        name: 'Model Studio',
        exact: true,
      }),
    ).toBeVisible();

    const customerNode = page.locator('app-model-studio-entity-node')
      .filter({ hasText: 'Customer' });

    await expect(customerNode).toHaveCount(1);
    await customerNode.click();

    const inspector = page.locator('app-model-studio-entity-inspector');

    await expect(
      inspector.locator('.field-card-name').getByText(fieldName, {
        exact: true,
      }),
    ).toBeVisible();
  });
});
