import { test as workspaceTest, expect, Page } from '../workspace/workspace.fixtures';

export interface ModelStudioContext {
  id: string;
  name: string;
  url: string;
}

async function fillCsvSection(
  page: Page,
  sectionName: string,
  csv: string,
): Promise<void> {
  await page.getByRole('tab', {
    name: sectionName,
    exact: true,
  }).click();

  await page.locator('#csv-section-input').fill(csv);
}

async function importPopulatedSpecification(
  page: Page,
  modelStudio: ModelStudioContext,
): Promise<void> {
  await page.getByRole('button', {
    name: /CSV Specification/,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelStudio.id}/specification-wizard$`),
  );

  await expect(
    page.getByRole('heading', {
      name: 'Define your Data Model',
      exact: true,
    }),
  ).toBeVisible();

  await fillCsvSection(
    page,
    'Entities',
    [
      'entity,description',
      'Customer,Customer master record',
      'Order,Customer order record',
    ].join('\n'),
  );

  await fillCsvSection(
    page,
    'Fields & Keys',
    [
      'entity,field,type,identity_position',
      'Customer,CUSTOMER_ID,IDENTIFIER,1',
      'Customer,CUSTOMER_NAME,STRING,',
      'Order,ORDER_ID,IDENTIFIER,1',
      'Order,CUSTOMER_ID,IDENTIFIER,',
      'Order,ORDER_NUMBER,STRING,',
    ].join('\n'),
  );

  await fillCsvSection(
    page,
    'Foreign Keys',
    [
      'source_entity,source_fields,target_entity',
      'Order,"[""CUSTOMER_ID""]",Customer',
    ].join('\n'),
  );

  await fillCsvSection(
    page,
    'Relationships',
    [
      'source_entity,target_entity,type',
      'Customer,Order,ONE_TO_MANY',
    ].join('\n'),
  );

  await page.getByRole('button', {
    name: /^Preview CSV import$/,
  }).click();

  const review = page.locator(
    'section[aria-label="CSV import review"]',
  );

  await expect(review).toBeVisible();

  await expect(
    review.getByText('Ready to apply', { exact: true }),
  ).toBeVisible({ timeout: 60_000 });

  await page.getByRole('button', {
    name: /Apply additions & open Model Studio/,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelStudio.id}/model-studio$`),
    { timeout: 60_000 },
  );

  await expect(
    page.getByRole('heading', {
      name: 'Model Studio',
      exact: true,
    }),
  ).toBeVisible();
}

export const test = workspaceTest.extend<{
  modelStudio: ModelStudioContext;
  populatedModelStudio: ModelStudioContext;
}>({
  modelStudio: async ({ page, workspaceModel }, use) => {
    await workspaceModel.card.click();

    await expect(page).toHaveURL(
      /\/workspace\/[^/]+\/model-studio$/,
      { timeout: 30_000 },
    );

    const modelStudioUrl = page.url();
    const match = modelStudioUrl.match(
      /\/workspace\/([^/]+)\/model-studio$/,
    );

    expect(
      match,
      'Expected to extract the test-owned Data Model ID from the Model Studio URL',
    ).not.toBeNull();

    await use({
      id: match![1],
      name: workspaceModel.name,
      url: modelStudioUrl,
    });
  },

  populatedModelStudio: async ({ page, modelStudio }, use) => {
    await importPopulatedSpecification(page, modelStudio);
    await use(modelStudio);
  },
});

export { expect };
