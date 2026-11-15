import { test, expect } from './model-studio.fixtures';

test.describe('MS02 - Entity creation', () => {
  test.describe.configure({ timeout: 120_000 });

  test('MS02-01: Open the create-entity dialog', async ({
    page,
    modelStudio,
  }) => {
    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelStudio.id}/model-studio$`),
    );

    await expect(
      page.locator('.canvas-empty-state'),
    ).toBeVisible();

    await page.locator(
      'app-specification-entry-panel',
    ).getByRole('button', {
      name: /Add Entity/,
    }).click();

    const dialog = page.getByRole('dialog', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(dialog).toBeVisible();

    await expect(
      dialog.locator('#entity-name'),
    ).toBeVisible();

    await expect(
      dialog.locator('#entity-description'),
    ).toBeVisible();

    await expect(
      dialog.locator('#entity-population'),
    ).toBeVisible();

    await expect(
      dialog.getByRole('button', {
        name: 'Add Entity',
        exact: true,
      }),
    ).toBeVisible();

    await expect(
      dialog.getByRole('button', {
        name: 'Cancel',
        exact: true,
      }),
    ).toBeVisible();
  });

  test('MS02-02: Create entity with valid name and description', async ({
    page,
    modelStudio,
  }) => {
    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelStudio.id}/model-studio$`),
    );

    const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const entityName = `E2E Entity ${uniqueId}`;
    const entityDescription = `Entity creation E2E test ${uniqueId}`;

    await page.locator(
      'app-specification-entry-panel',
    ).getByRole('button', {
      name: /Add Entity/,
    }).click();

    const dialog = page.getByRole('dialog', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(dialog).toBeVisible();

    await dialog.locator('#entity-name').fill(entityName);
    await dialog.locator('#entity-description').fill(entityDescription);

    const saveButton = dialog.getByRole('button', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(saveButton).toBeEnabled();

    const createResponsePromise = page.waitForResponse((response) => {
      const request = response.request();
      const pathname = new URL(response.url()).pathname;

      return (
        request.method() === 'POST' &&
        pathname.endsWith(
          `/data-models/${modelStudio.id}/specification/entities`,
        )
      );
    });

    await saveButton.click();

    const createResponse = await createResponsePromise;

    expect(
      createResponse.status(),
      'Entity creation should return HTTP 201',
    ).toBe(201);

    const createdEntity = await createResponse.json();

    expect(createdEntity.name).toBe(entityName);
    expect(createdEntity.description).toBe(entityDescription);
    expect(createdEntity.fields).toEqual([]);
    expect(createdEntity.population).toEqual({
      count: 100,
      scaling: 'SCALABLE',
    });

    await expect(dialog).toBeHidden();

    const entityNodes = page.locator('app-model-studio-entity-node');

    await expect(entityNodes).toHaveCount(1);

    await expect(
      entityNodes.filter({ hasText: entityName }),
    ).toHaveCount(1);

    await page.reload();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelStudio.id}/model-studio$`),
    );

    await expect(
      page.getByRole('heading', {
        name: 'Model Studio',
        exact: true,
      }),
    ).toBeVisible();

    await expect(entityNodes).toHaveCount(1);

    await expect(
      entityNodes.filter({ hasText: entityName }),
    ).toHaveCount(1);
  });

  test('MS02-03: Create entity with custom population settings', async ({
    page,
    modelStudio,
  }) => {
    const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const entityName = `E2E Population Entity ${uniqueId}`;
    const entityDescription = `Custom population E2E test ${uniqueId}`;

    await page.locator(
      'app-specification-entry-panel',
    ).getByRole('button', {
      name: /Add Entity/,
    }).click();

    const dialog = page.getByRole('dialog', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(dialog).toBeVisible();

    await dialog.locator('#entity-name').fill(entityName);
    await dialog.locator('#entity-description').fill(entityDescription);
    await dialog.locator('#entity-population').fill('250');

    await dialog.locator(
      'input[name="population-scaling"][value="FIXED"]',
    ).check();

    await expect(
      dialog.locator('#entity-population'),
    ).toHaveValue('250');

    await expect(
      dialog.locator('input[name="population-scaling"][value="FIXED"]'),
    ).toBeChecked();

    const createResponsePromise = page.waitForResponse((response) => {
      const request = response.request();
      const pathname = new URL(response.url()).pathname;

      return (
        request.method() === 'POST' &&
        pathname.endsWith(
          `/data-models/${modelStudio.id}/specification/entities`,
        )
      );
    });

    await dialog.getByRole('button', {
      name: 'Add Entity',
      exact: true,
    }).click();

    const createResponse = await createResponsePromise;

    expect(
      createResponse.status(),
      'Entity creation should return HTTP 201',
    ).toBe(201);

    const createdEntity = await createResponse.json();

    expect(createdEntity.name).toBe(entityName);
    expect(createdEntity.description).toBe(entityDescription);
    expect(createdEntity.population).toEqual({
      count: 250,
      scaling: 'FIXED',
    });

    await expect(dialog).toBeHidden();

    const entityNodes = page.locator('app-model-studio-entity-node');

    await expect(
      entityNodes.filter({ hasText: entityName }),
    ).toHaveCount(1);
  });


  test('MS02-04: Prevent entity creation when required name is missing', async ({
    page,
    modelStudio,
  }) => {
    await page.locator(
      'app-specification-entry-panel',
    ).getByRole('button', {
      name: /Add Entity/,
    }).click();

    const dialog = page.getByRole('dialog', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(dialog).toBeVisible();

    const nameInput = dialog.locator('#entity-name');
    const descriptionInput = dialog.locator('#entity-description');

    await expect(nameInput).toHaveValue('');

    await descriptionInput.fill(
      'Entity creation validation test with a missing name.',
    );

    await dialog.locator('#entity-population').fill('100');

    const saveButton = dialog.getByRole('button', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(saveButton).toBeDisabled();

    await expect(nameInput).toHaveValue('');
    await expect(dialog).toBeVisible();

    await expect(
      page.locator('app-model-studio-entity-node'),
    ).toHaveCount(0);
  });


  test('MS02-05: Reject duplicate entity name', async ({
    page,
    modelStudio,
  }) => {
    const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const entityName = `E2E Duplicate Entity ${uniqueId}`;
    const originalDescription = `Original entity ${uniqueId}`;
    const duplicateDescription = `Duplicate attempt ${uniqueId}`;

    const openDialog = async () => {
      await page.locator(
        'app-specification-entry-panel',
      ).getByRole('button', {
        name: /Add Entity/,
      }).click();

      const dialog = page.getByRole('dialog', {
        name: 'Add Entity',
        exact: true,
      });

      await expect(dialog).toBeVisible();
      return dialog;
    };

    const createResponse = async (dialog: ReturnType<typeof page.getByRole>) => {
      const responsePromise = page.waitForResponse((response) => {
        const request = response.request();
        const pathname = new URL(response.url()).pathname;

        return (
          request.method() === 'POST' &&
          pathname.endsWith(
            `/data-models/${modelStudio.id}/specification/entities`,
          )
        );
      });

      await dialog.getByRole('button', {
        name: 'Add Entity',
        exact: true,
      }).click();

      return responsePromise;
    };

    // Create the original entity.
    const originalDialog = await openDialog();

    await originalDialog.locator('#entity-name').fill(entityName);
    await originalDialog.locator('#entity-description').fill(originalDescription);

    const originalResponse = await createResponse(originalDialog);

    expect(originalResponse.status()).toBe(201);

    const originalEntity = await originalResponse.json();

    expect(originalEntity.name).toBe(entityName);
    expect(originalEntity.description).toBe(originalDescription);

    await expect(originalDialog).toBeHidden();

    // Attempt to create another entity with the same name.
    const duplicateDialog = await openDialog();

    await duplicateDialog.locator('#entity-name').fill(entityName);
    await duplicateDialog.locator('#entity-description').fill(duplicateDescription);

    const duplicateResponse = await createResponse(duplicateDialog);

    expect(
      duplicateResponse.status(),
      'Duplicate entity creation should return HTTP 409 Conflict',
    ).toBe(409);

    const duplicateError = await duplicateResponse.json();

    expect(duplicateError.detail).toBe(
      `Entity already exists: ${entityName}`,
    );

    // The duplicate attempt must not replace the original entity.
    await expect(duplicateDialog).toBeVisible();

    const entityNodes = page.locator('app-model-studio-entity-node');

    await expect(entityNodes).toHaveCount(1);

    await expect(
      entityNodes.filter({ hasText: entityName }),
    ).toHaveCount(1);

    await expect(
      duplicateDialog.locator('#entity-name'),
    ).toHaveValue(entityName);
  });


  test('MS02-06: Cancel entity creation', async ({
    page,
    modelStudio,
  }) => {
    const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const entityName = `E2E Cancelled Entity ${uniqueId}`;

    await page.locator(
      'app-specification-entry-panel',
    ).getByRole('button', {
      name: /Add Entity/,
    }).click();

    const dialog = page.getByRole('dialog', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(dialog).toBeVisible();

    await dialog.locator('#entity-name').fill(entityName);
    await dialog.locator('#entity-description').fill(
      'This entity should not be created.',
    );

    await expect(
      dialog.getByRole('button', {
        name: 'Add Entity',
        exact: true,
      }),
    ).toBeEnabled();

    await dialog.getByRole('button', {
      name: 'Cancel',
      exact: true,
    }).click();

    await expect(dialog).toBeHidden();

    await expect(
      page.locator('app-model-studio-entity-node'),
    ).toHaveCount(0);

    await page.reload();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelStudio.id}/model-studio$`),
    );

    await expect(
      page.locator('app-model-studio-entity-node'),
    ).toHaveCount(0);

    await expect(
      page.getByText(entityName, { exact: true }),
    ).toHaveCount(0);
  });


  test('MS02-07: Verify entity persistence after reload', async ({
    page,
    modelStudio,
  }) => {
    const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const entityName = `E2E Persistence Entity ${uniqueId}`;
    const entityDescription = `Persistence verification ${uniqueId}`;

    await page.locator(
      'app-specification-entry-panel',
    ).getByRole('button', {
      name: /Add Entity/,
    }).click();

    const dialog = page.getByRole('dialog', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(dialog).toBeVisible();

    await dialog.locator('#entity-name').fill(entityName);
    await dialog.locator('#entity-description').fill(entityDescription);
    await dialog.locator('#entity-population').fill('375');

    await dialog.locator(
      'input[name="population-scaling"][value="FIXED"]',
    ).check();

    const createResponsePromise = page.waitForResponse((response) => {
      const request = response.request();
      const pathname = new URL(response.url()).pathname;

      return (
        request.method() === 'POST' &&
        pathname.endsWith(
          `/data-models/${modelStudio.id}/specification/entities`,
        )
      );
    });

    await dialog.getByRole('button', {
      name: 'Add Entity',
      exact: true,
    }).click();

    const createResponse = await createResponsePromise;

    expect(createResponse.status()).toBe(201);

    const createdEntity = await createResponse.json();

    expect(createdEntity.name).toBe(entityName);
    expect(createdEntity.description).toBe(entityDescription);
    expect(createdEntity.population).toEqual({
      count: 375,
      scaling: 'FIXED',
    });

    await expect(dialog).toBeHidden();

    await page.reload();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelStudio.id}/model-studio$`),
    );

    await expect(
      page.getByRole('heading', {
        name: 'Model Studio',
        exact: true,
      }),
    ).toBeVisible();

    const entityNode = page.locator(
      'app-model-studio-entity-node',
    ).filter({ hasText: entityName });

    await expect(entityNode).toHaveCount(1);
    await expect(entityNode).toContainText(entityName);

    await entityNode.click();

    const inspector = page.locator('app-inspector-header');

    await expect(inspector).toContainText(entityName);
    await expect(inspector).toContainText('375');
  });

});
