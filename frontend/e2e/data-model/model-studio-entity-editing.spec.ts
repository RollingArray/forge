import { test, expect } from './model-studio.fixtures';

test.describe('MS03 - Entity editing', () => {
  test.describe.configure({ timeout: 120_000 });

  test('MS03-01: Open an existing entity for editing', async ({
    page,
    modelStudio,
  }) => {
    const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const entityName = `E2E Edit Entity ${uniqueId}`;
    const entityDescription = `Original entity description ${uniqueId}`;

    // Create an entity with non-default values to verify edit-mode population.
    await page.locator(
      'app-specification-entry-panel',
    ).getByRole('button', {
      name: /Add Entity/,
    }).click();

    const createDialog = page.getByRole('dialog', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(createDialog).toBeVisible();

    await createDialog.locator('#entity-name').fill(entityName);
    await createDialog.locator('#entity-description').fill(entityDescription);
    await createDialog.locator('#entity-population').fill('375');

    await createDialog.locator(
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

    await createDialog.getByRole('button', {
      name: 'Add Entity',
      exact: true,
    }).click();

    const createResponse = await createResponsePromise;

    expect(createResponse.status()).toBe(201);
    await expect(createDialog).toBeHidden();

    // Select the entity and open its edit dialog.
    const entityNode = page.locator(
      'app-model-studio-entity-node',
    ).filter({ hasText: entityName });

    await expect(entityNode).toHaveCount(1);
    await entityNode.click();

    const inspector = page.locator('app-model-studio-entity-inspector');

    await expect(inspector).toBeVisible();

    await inspector.locator('.edit-button').click();

    const editDialog = page.getByRole('dialog', {
      name: 'Edit Entity',
      exact: true,
    });

    await expect(editDialog).toBeVisible();

    // Verify that existing values populate the edit form.
    const nameInput = editDialog.locator('#entity-name');
    const descriptionInput = editDialog.locator('#entity-description');
    const populationInput = editDialog.locator('#entity-population');

    await expect(nameInput).toHaveValue(entityName);
    await expect(nameInput).toHaveAttribute('readonly', '');

    await expect(descriptionInput).toHaveValue(entityDescription);
    await expect(populationInput).toHaveValue('375');

    await expect(
      editDialog.locator(
        'input[name="population-scaling"][value="FIXED"]',
      ),
    ).toBeChecked();

    await expect(
      editDialog.getByRole('button', {
        name: 'Save Changes',
        exact: true,
      }),
    ).toBeVisible();

    await expect(
      editDialog.getByRole('button', {
        name: 'Cancel',
        exact: true,
      }),
    ).toBeVisible();
  });

  test('MS03-02: Update entity description', async ({
    page,
    modelStudio,
  }) => {
    const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const entityName = `E2E Description Entity ${uniqueId}`;
    const originalDescription = `Original description ${uniqueId}`;
    const updatedDescription = `Updated description ${uniqueId}`;

    // Create the entity.
    await page.locator(
      'app-specification-entry-panel',
    ).getByRole('button', {
      name: /Add Entity/,
    }).click();

    const createDialog = page.getByRole('dialog', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(createDialog).toBeVisible();
    await createDialog.locator('#entity-name').fill(entityName);
    await createDialog.locator('#entity-description').fill(originalDescription);

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

    await createDialog.getByRole('button', {
      name: 'Add Entity',
      exact: true,
    }).click();

    const createResponse = await createResponsePromise;
    expect(createResponse.status()).toBe(201);
    await expect(createDialog).toBeHidden();

    // Select the entity and open edit mode.
    const entityNode = page.locator(
      'app-model-studio-entity-node',
    ).filter({ hasText: entityName });

    await expect(entityNode).toHaveCount(1);
    await entityNode.click();

    const inspector = page.locator('app-model-studio-entity-inspector');
    await inspector.locator('.edit-button').click();

    const editDialog = page.getByRole('dialog', {
      name: 'Edit Entity',
      exact: true,
    });

    await expect(editDialog).toBeVisible();
    await expect(
      editDialog.locator('#entity-description'),
    ).toHaveValue(originalDescription);

    await editDialog.locator('#entity-description').fill(updatedDescription);

    const updateResponsePromise = page.waitForResponse((response) => {
      const request = response.request();
      const pathname = new URL(response.url()).pathname;

      return (
        request.method() === 'PUT' &&
        pathname.includes(
          `/data-models/${modelStudio.id}/specification/entities/`,
        )
      );
    });

    await editDialog.getByRole('button', {
      name: 'Save Changes',
      exact: true,
    }).click();

    const updateResponse = await updateResponsePromise;

    expect(
      updateResponse.status(),
      'Entity update should return HTTP 200',
    ).toBe(200);

    const updatedEntity = await updateResponse.json();

    expect(updatedEntity.name).toBe(entityName);
    expect(updatedEntity.description).toBe(updatedDescription);

    await expect(editDialog).toBeHidden();

    // Verify the updated description in the inspector.
    await entityNode.click();

    const entityDescription = page.locator(
      'app-model-studio-entity-inspector .entity-description',
    );

    await expect(entityDescription).toHaveText(updatedDescription);

    // Reload and verify that the description remains persisted.
    await page.reload();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelStudio.id}/model-studio$`),
    );

    const reloadedEntityNode = page.locator(
      'app-model-studio-entity-node',
    ).filter({ hasText: entityName });

    await expect(reloadedEntityNode).toHaveCount(1);
    await reloadedEntityNode.click();

    await expect(
      page.locator(
        'app-model-studio-entity-inspector .entity-description',
      ),
    ).toHaveText(updatedDescription);
  });


  test('MS03-03: Update population', async ({
    page,
    modelStudio,
  }) => {
    const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const entityName = `E2E Population Edit ${uniqueId}`;
    const entityDescription = `Population editing test ${uniqueId}`;
    const originalPopulation = '250';
    const updatedPopulation = '600';

    // Create an entity with a known population and scaling configuration.
    await page.locator(
      'app-specification-entry-panel',
    ).getByRole('button', {
      name: /Add Entity/,
    }).click();

    const createDialog = page.getByRole('dialog', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(createDialog).toBeVisible();
    await createDialog.locator('#entity-name').fill(entityName);
    await createDialog.locator('#entity-description').fill(entityDescription);
    await createDialog.locator('#entity-population').fill(originalPopulation);

    await createDialog.locator(
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

    await createDialog.getByRole('button', {
      name: 'Add Entity',
      exact: true,
    }).click();

    const createResponse = await createResponsePromise;
    expect(createResponse.status()).toBe(201);

    const createdEntity = await createResponse.json();

    expect(createdEntity.population).toEqual({
      count: 250,
      scaling: 'FIXED',
    });

    await expect(createDialog).toBeHidden();

    // Select the entity and open edit mode.
    const entityNode = page.locator(
      'app-model-studio-entity-node',
    ).filter({ hasText: entityName });

    await expect(entityNode).toHaveCount(1);
    await entityNode.click();

    const inspector = page.locator('app-model-studio-entity-inspector');
    await inspector.locator('.edit-button').click();

    const editDialog = page.getByRole('dialog', {
      name: 'Edit Entity',
      exact: true,
    });

    await expect(editDialog).toBeVisible();

    await expect(
      editDialog.locator('#entity-population'),
    ).toHaveValue(originalPopulation);

    await expect(
      editDialog.locator(
        'input[name="population-scaling"][value="FIXED"]',
      ),
    ).toBeChecked();

    // Change only the population.
    await editDialog.locator('#entity-population').fill(updatedPopulation);

    const updateResponsePromise = page.waitForResponse((response) => {
      const request = response.request();
      const pathname = new URL(response.url()).pathname;

      return (
        request.method() === 'PUT' &&
        pathname.includes(
          `/data-models/${modelStudio.id}/specification/entities/`,
        )
      );
    });

    await editDialog.getByRole('button', {
      name: 'Save Changes',
      exact: true,
    }).click();

    const updateResponse = await updateResponsePromise;

    expect(
      updateResponse.status(),
      'Population update should return HTTP 200',
    ).toBe(200);

    const updatedEntity = await updateResponse.json();

    expect(updatedEntity.name).toBe(entityName);
    expect(updatedEntity.description).toBe(entityDescription);
    expect(updatedEntity.population).toEqual({
      count: 600,
      scaling: 'FIXED',
    });

    await expect(editDialog).toBeHidden();

    // Verify the updated population in the inspector.
    await entityNode.click();

    const inspectorHeader = page.locator('app-inspector-header');

    await expect(inspectorHeader).toContainText('600');

    // Reload and verify persistence.
    await page.reload();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelStudio.id}/model-studio$`),
    );

    const reloadedEntityNode = page.locator(
      'app-model-studio-entity-node',
    ).filter({ hasText: entityName });

    await expect(reloadedEntityNode).toHaveCount(1);
    await reloadedEntityNode.click();

    await expect(
      page.locator('app-inspector-header'),
    ).toContainText('600');

    await expect(
      page.locator('app-inspector-header'),
    ).toContainText(entityDescription);
  });


  test('MS03-04: Attempt invalid entity update', async ({
    page,
    modelStudio,
  }) => {
    const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const entityName = `E2E Invalid Edit ${uniqueId}`;
    const entityDescription = `Invalid update test ${uniqueId}`;

    // Create an entity with a valid population.
    await page.locator(
      'app-specification-entry-panel',
    ).getByRole('button', {
      name: /Add Entity/,
    }).click();

    const createDialog = page.getByRole('dialog', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(createDialog).toBeVisible();
    await createDialog.locator('#entity-name').fill(entityName);
    await createDialog.locator('#entity-description').fill(entityDescription);
    await createDialog.locator('#entity-population').fill('100');

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

    await createDialog.getByRole('button', {
      name: 'Add Entity',
      exact: true,
    }).click();

    const createResponse = await createResponsePromise;
    expect(createResponse.status()).toBe(201);
    await expect(createDialog).toBeHidden();

    // Open the newly created entity for editing.
    const entityNode = page.locator(
      'app-model-studio-entity-node',
    ).filter({ hasText: entityName });

    await expect(entityNode).toHaveCount(1);
    await entityNode.click();

    const inspector = page.locator('app-model-studio-entity-inspector');
    await inspector.locator('.edit-button').click();

    const editDialog = page.getByRole('dialog', {
      name: 'Edit Entity',
      exact: true,
    });

    await expect(editDialog).toBeVisible();

    const populationInput = editDialog.locator('#entity-population');
    await expect(populationInput).toHaveValue('100');

    await populationInput.fill('-1');

    // The invalid population must disable saving.
    await expect(
      editDialog.getByRole('button', {
        name: 'Save Changes',
        exact: true,
      }),
    ).toBeDisabled();

    await expect(populationInput).toHaveValue('-1');
    await expect(editDialog).toBeVisible();
  });


  test('MS03-05: Cancel editing', async ({
    page,
    modelStudio,
  }) => {
    const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const entityName = `E2E Cancel Edit ${uniqueId}`;
    const originalDescription = `Original description ${uniqueId}`;
    const changedDescription = `Changed description ${uniqueId}`;

    // Create an entity with known values.
    await page.locator(
      'app-specification-entry-panel',
    ).getByRole('button', {
      name: /Add Entity/,
    }).click();

    const createDialog = page.getByRole('dialog', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(createDialog).toBeVisible();
    await createDialog.locator('#entity-name').fill(entityName);
    await createDialog.locator('#entity-description').fill(originalDescription);
    await createDialog.locator('#entity-population').fill('300');

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

    await createDialog.getByRole('button', {
      name: 'Add Entity',
      exact: true,
    }).click();

    const createResponse = await createResponsePromise;
    expect(createResponse.status()).toBe(201);
    await expect(createDialog).toBeHidden();

    // Open the entity for editing.
    const entityNode = page.locator(
      'app-model-studio-entity-node',
    ).filter({ hasText: entityName });

    await expect(entityNode).toHaveCount(1);
    await entityNode.click();

    const inspector = page.locator('app-model-studio-entity-inspector');
    await inspector.locator('.edit-button').click();

    const editDialog = page.getByRole('dialog', {
      name: 'Edit Entity',
      exact: true,
    });

    await expect(editDialog).toBeVisible();

    // Change the description and population, then cancel.
    await editDialog.locator('#entity-description').fill(changedDescription);
    await editDialog.locator('#entity-population').fill('900');

    const updateRequests: string[] = [];
    page.on('request', (request) => {
      const pathname = new URL(request.url()).pathname;

      if (
        request.method() === 'PUT' &&
        pathname.includes(
          `/data-models/${modelStudio.id}/specification/entities/`,
        )
      ) {
        updateRequests.push(request.url());
      }
    });

    await editDialog.getByRole('button', {
      name: 'Cancel',
      exact: true,
    }).click();

    await expect(editDialog).toBeHidden();

    // Reopen the entity and verify the original values remain unchanged.
    await entityNode.click();
    await inspector.locator('.edit-button').click();

    const reopenedDialog = page.getByRole('dialog', {
      name: 'Edit Entity',
      exact: true,
    });

    await expect(reopenedDialog).toBeVisible();
    await expect(
      reopenedDialog.locator('#entity-description'),
    ).toHaveValue(originalDescription);
    await expect(
      reopenedDialog.locator('#entity-population'),
    ).toHaveValue('300');

    expect(
      updateRequests,
      'Cancelling the edit must not submit an entity update',
    ).toHaveLength(0);
  });


  test('MS03-06: Reload after editing', async ({
    page,
    modelStudio,
  }) => {
    const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const entityName = `E2E Reload Edit ${uniqueId}`;
    const originalDescription = `Original reload description ${uniqueId}`;
    const updatedDescription = `Updated reload description ${uniqueId}`;

    // Create an entity with known initial values.
    await page.locator(
      'app-specification-entry-panel',
    ).getByRole('button', {
      name: /Add Entity/,
    }).click();

    const createDialog = page.getByRole('dialog', {
      name: 'Add Entity',
      exact: true,
    });

    await expect(createDialog).toBeVisible();
    await createDialog.locator('#entity-name').fill(entityName);
    await createDialog.locator('#entity-description').fill(originalDescription);
    await createDialog.locator('#entity-population').fill('200');

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

    await createDialog.getByRole('button', {
      name: 'Add Entity',
      exact: true,
    }).click();

    const createResponse = await createResponsePromise;
    expect(createResponse.status()).toBe(201);
    await expect(createDialog).toBeHidden();

    // Open the entity for editing.
    const entityNode = page.locator(
      'app-model-studio-entity-node',
    ).filter({ hasText: entityName });

    await expect(entityNode).toHaveCount(1);
    await entityNode.click();

    const inspector = page.locator('app-model-studio-entity-inspector');
    await inspector.locator('.edit-button').click();

    const editDialog = page.getByRole('dialog', {
      name: 'Edit Entity',
      exact: true,
    });

    await expect(editDialog).toBeVisible();

    // Update the description and population.
    await editDialog.locator('#entity-description').fill(updatedDescription);
    await editDialog.locator('#entity-population').fill('750');

    const updateResponsePromise = page.waitForResponse((response) => {
      const request = response.request();
      const pathname = new URL(response.url()).pathname;

      return (
        request.method() === 'PUT' &&
        pathname.includes(
          `/data-models/${modelStudio.id}/specification/entities/`,
        )
      );
    });

    await editDialog.getByRole('button', {
      name: 'Save Changes',
      exact: true,
    }).click();

    const updateResponse = await updateResponsePromise;
    expect(updateResponse.status()).toBe(200);

    const updatedEntity = await updateResponse.json();

    expect(updatedEntity.name).toBe(entityName);
    expect(updatedEntity.description).toBe(updatedDescription);
    expect(updatedEntity.population).toEqual({
      count: 750,
      scaling: 'SCALABLE',
    });

    await expect(editDialog).toBeHidden();

    // Reload the browser and verify the entity still exists.
    await page.reload();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelStudio.id}/model-studio$`),
    );

    const reloadedEntityNode = page.locator(
      'app-model-studio-entity-node',
    ).filter({ hasText: entityName });

    await expect(reloadedEntityNode).toHaveCount(1);
    await reloadedEntityNode.click();

    // Verify persisted values through the entity inspector.
    const reloadedInspector = page.locator('app-model-studio-entity-inspector');

    await expect(reloadedInspector).toContainText(updatedDescription);
    await expect(
      page.locator('app-inspector-header'),
    ).toContainText('750');

    // Reopen edit mode and verify the persisted form values.
    await reloadedInspector.locator('.edit-button').click();

    const reloadedEditDialog = page.getByRole('dialog', {
      name: 'Edit Entity',
      exact: true,
    });

    await expect(reloadedEditDialog).toBeVisible();
    await expect(
      reloadedEditDialog.locator('#entity-description'),
    ).toHaveValue(updatedDescription);
    await expect(
      reloadedEditDialog.locator('#entity-population'),
    ).toHaveValue('750');
  });

});
