import { test, expect } from './model-studio.fixtures';

test.describe('MS01 - Model Studio entry and navigation', () => {
  test.describe.configure({ timeout: 120_000 });
  test('MS01-01: Open Model Studio for a valid data model', async ({
    page,
    workspaceModel,
    modelStudio,
  }) => {
    expect(modelStudio.id).toBeTruthy();
    expect(modelStudio.name).toBe(workspaceModel.name);

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelStudio.id}/model-studio$`),
    );

    await expect(
      page.getByRole('heading', {
        name: 'Model Studio',
        exact: true,
      }),
    ).toBeVisible();

    await expect(
      page.getByRole('button', {
        name: /CSV Specification/,
      }),
    ).toBeVisible();

    await expect(
      page.locator('app-model-studio-canvas'),
    ).toBeVisible();
  });

  test('MS01-02: Load an existing specification', async ({
    page,
    populatedModelStudio,
  }) => {
    await expect(page).toHaveURL(
      new RegExp(`/workspace/${populatedModelStudio.id}/model-studio$`),
    );

    const entityNodes = page.locator(
      'app-model-studio-entity-node',
    );

    await expect(entityNodes).toHaveCount(2);

    await expect(
      entityNodes.filter({ hasText: 'Customer' }),
    ).toHaveCount(1);

    await expect(
      entityNodes.filter({ hasText: 'Order' }),
    ).toHaveCount(1);

    await expect(
      page.locator(
        'app-model-studio-relationship-layer .relationship-line',
      ),
    ).toHaveCount(1);
  });

  test('MS01-03: Open a model with no entities', async ({
    page,
    modelStudio,
  }) => {
    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelStudio.id}/model-studio$`),
    );

    const emptyState = page.locator('.canvas-empty-state');

    await expect(emptyState).toBeVisible();

    await expect(
      emptyState.getByRole('heading', {
        name: 'Start building your model',
        exact: true,
      }),
    ).toBeVisible();

    await expect(
      emptyState.getByText(
        'This Data Model does not have any entities yet.',
        { exact: true },
      ),
    ).toBeVisible();

    await expect(
      page.locator('app-model-studio-entity-node'),
    ).toHaveCount(0);
  });

  test('MS01-04: Navigate between Model Studio and validation', async ({
    page,
    populatedModelStudio,
  }) => {
    await expect(page).toHaveURL(
      new RegExp(`/workspace/${populatedModelStudio.id}/model-studio$`),
    );

    await page.getByRole('button', {
      name: 'Continue to Validation',
      exact: true,
    }).click();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${populatedModelStudio.id}/model-validation$`),
    );

    await expect(
      page.getByRole('heading', {
        name: 'Model Validation',
        exact: true,
      }),
    ).toBeVisible();

    await page.getByRole('button', {
      name: 'Back to Model',
      exact: true,
    }).click();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${populatedModelStudio.id}/model-studio$`),
    );

    await expect(
      page.getByRole('heading', {
        name: 'Model Studio',
        exact: true,
      }),
    ).toBeVisible();

    await expect(
      page.locator('app-model-studio-entity-node'),
    ).toHaveCount(2);

    await expect(
      page.locator(
        'app-model-studio-relationship-layer .relationship-line',
      ),
    ).toHaveCount(1);
  });

  test('MS01-05: Handle an unavailable specification', async ({
    page,
    modelStudio,
  }) => {
    const specificationPath =
      `/data-models/${modelStudio.id}/specification`;

    await page.route('**/data-models/**/specification', async (route) => {
      const requestUrl = new URL(route.request().url());

      if (requestUrl.pathname.endsWith(specificationPath)) {
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Data Model specification not found',
          }),
        });
        return;
      }

      await route.continue();
    });

    await page.reload();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelStudio.id}/model-studio$`),
    );

    await expect(
      page.getByRole('heading', {
        name: 'Unable to load Model Studio',
        exact: true,
      }),
    ).toBeVisible();

    await expect(
      page.getByText(
        'Unable to load the Data Model specification.',
        { exact: true },
      ),
    ).toBeVisible();

    await expect(
      page.locator('app-model-studio-entity-node'),
    ).toHaveCount(0);
  });

  test('MS01-06: Reload Model Studio', async ({
    page,
    populatedModelStudio,
  }) => {
    await expect(
      page.locator('app-model-studio-entity-node'),
    ).toHaveCount(2);

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

    await expect(
      page.locator('app-model-studio-entity-node'),
    ).toHaveCount(2);

    await expect(
      page.locator(
        'app-model-studio-relationship-layer .relationship-line',
      ),
    ).toHaveCount(1);
  });
});
