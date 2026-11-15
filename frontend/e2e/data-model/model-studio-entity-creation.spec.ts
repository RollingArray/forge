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
});
