import { test, expect } from '@playwright/test';

test('WP02: create Data Model and import Aerospace sample through UI', async ({
  page,
}, testInfo) => {
  test.setTimeout(180_000);

  const modelName =
    `FORGE WP02 E2E ${new Date().toISOString().replace(/[:.]/g, '-')}`;

  console.log(`Creating test model: ${modelName}`);

  // --------------------------------------------------
  // 1. Open authenticated Workspace
  // --------------------------------------------------

  await page.goto('/workspace');

  await expect(page).toHaveURL(/\/workspace/);

  // --------------------------------------------------
  // 2. Create a fresh Data Model
  // --------------------------------------------------

  await page.locator('button.new-dataModel-button').click();

  await page.locator('#data-model-name').fill(modelName);

  await page
    .locator('#data-model-description')
    .fill('Automated WP-02 browser acceptance test model.');

  await page.locator('button.save-button').click();

  await expect(page).toHaveURL(/\/workspace\/[^/]+\/model-studio/);

  const modelStudioUrl = new URL(page.url());
  const modelId = modelStudioUrl.pathname.split('/')[2];

  expect(modelId).toBeTruthy();

  console.log(`Created Data Model ID: ${modelId}`);

  await testInfo.attach('created-data-model', {
    body: JSON.stringify(
      {
        name: modelName,
        dataModelId: modelId,
        modelStudioUrl: page.url(),
      },
      null,
      2,
    ),
    contentType: 'application/json',
  });

  // --------------------------------------------------
  // 3. Open CSV Specification Wizard
  // --------------------------------------------------

  await page
    .getByRole('button', { name: /CSV Specification/ })
    .click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelId}/specification-wizard`),
  );

  await expect(
    page.getByRole('heading', { name: 'Define your Data Model' }),
  ).toBeVisible();

  // --------------------------------------------------
  // 4. Load all five Aerospace sample sections
  // --------------------------------------------------

  await page
    .getByRole('button', { name: 'Load Complete Aerospace Sample' })
    .click();

  const sections = [
    {
      name: 'Entities',
      header: 'entity,description,population_count,population_scaling',
    },
    {
      name: 'Fields & Keys',
      header: 'entity,field,type,identity_position',
    },
    {
      name: 'Foreign Keys',
      header: 'source_entity,source_fields,target_entity',
    },
    {
      name: 'Relationships',
      header: 'source_entity,target_entity,type',
    },
    {
      name: 'Constraints',
      header: 'entity,field,operator,value',
    },
  ];

  for (const section of sections) {
    const tab = page.getByRole('tab', {
      name: new RegExp(section.name.replace('&', '\\&')),
    });

    await expect(tab).toBeVisible();

    await tab.click();

    const textarea = page.locator('#csv-section-input');

    await expect(textarea).not.toHaveValue('');

    await expect(textarea).toHaveValue(
      new RegExp(`^${section.header.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`),
    );

    console.log(`PASS: ${section.name} CSV loaded`);
  }

  // --------------------------------------------------
  // 5. Preview the import
  // --------------------------------------------------

  await page
    .getByRole('button', { name: /Preview CSV import/ })
    .click();

  const review = page.locator(
    'section[aria-label="CSV import review"]',
  );

  await expect(review).toBeVisible();

  await expect(
    review.getByText('Ready to apply'),
  ).toBeVisible();

  // --------------------------------------------------
  // 6. Apply only when the backend says it is ready
  // --------------------------------------------------

  const applyButton = page.getByRole('button', {
    name: /Apply additions & open Model Studio/,
  });

  await expect(applyButton).toBeEnabled();

  await applyButton.click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelId}/model-studio`),
    { timeout: 60_000 },
  );

  console.log('PASS: Aerospace sample import applied.');
  console.log(`Retained test model: ${modelName}`);
  console.log(`Data Model ID: ${modelId}`);

  // --------------------------------------------------
  // 7. WP02: Model Validation UI acceptance
  // --------------------------------------------------

  await page.getByRole('button', {
    name: 'Validation',
    exact: true,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelId}/model-validation$`),
  );

  await expect(
    page.getByText('Model Validation', { exact: true }),
  ).toBeVisible();

  const validationReady = page.getByText(
    'Ready for Population',
    { exact: true },
  );

  const validationBlocked = page.getByText(
    'Requires Attention',
    { exact: true },
  );

  await expect(
    validationReady.or(validationBlocked),
  ).toBeVisible({ timeout: 60_000 });

  const canContinue = await validationReady.isVisible();

  await page.screenshot({
    path: test.info().outputPath('wp02-model-validation.png'),
    fullPage: true,
  });

  console.log(
    `WP02 Model Validation: ${
      canContinue ? 'READY FOR POPULATION' : 'REQUIRES ATTENTION'
    }`,
  );

  // --------------------------------------------------
  // 8. WP02: Population Plan UI acceptance
  // --------------------------------------------------

  await page.getByRole('button', {
    name: 'Population Plan',
    exact: true,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelId}/data-model/population$`),
  );

  await expect(
    page.getByRole('heading', { name: 'Population Plan', exact: true }),
  ).toBeVisible();

  if (canContinue) {
    await expect(
      page.getByText('Population overview', { exact: true }),
    ).toBeVisible({ timeout: 60_000 });

    await expect(
      page.getByText('Entity Population Plan', { exact: true }),
    ).toBeVisible();

    console.log('WP02 Population Plan: OVERVIEW AND ENTITY TABLE LOADED');
  } else {
    await expect(
      page.getByText('POPULATION PLAN BLOCKED', { exact: true }),
    ).toBeVisible({ timeout: 60_000 });

    console.log('WP02 Population Plan: CORRECTLY BLOCKED BY VALIDATION');
  }

  await page.screenshot({
    path: test.info().outputPath('wp02-population-plan.png'),
    fullPage: true,
  });

  // --------------------------------------------------
  // 9. WP02 UI-01: Standard population allocation
  // --------------------------------------------------

  if (canContinue) {
    const targetInput = page.locator('#population-target');

    await expect(targetInput).toBeVisible();
    await targetInput.fill('1000');
    await page.locator('.population-target-button').click();

    const candidateHeading = page.locator('strong').filter({
      hasText: /Candidate plan is feasible|Target cannot be achieved with this driver|Allocation cannot be verified|Allocation needs review/,
    });

    await expect(candidateHeading).toBeVisible({
      timeout: 60_000,
    });

    const candidateDecision = await candidateHeading.innerText();

    console.log(`WP02 UI-01 Candidate decision: ${candidateDecision}`);

    await page.screenshot({
      path: test.info().outputPath('wp02-population-candidate.png'),
      fullPage: true,
    });

    const businessUnitRow = page
      .locator('.simple-table-row')
      .filter({ hasText: 'BUSINESS_UNIT' });

    await expect(businessUnitRow).toHaveCount(1);

    const businessUnitCells = businessUnitRow.locator(':scope > span');

    await expect(businessUnitCells.nth(2)).toHaveText('FIXED');
    await expect(businessUnitCells.nth(4)).toHaveText('4');
    await expect(businessUnitCells.nth(6)).toHaveText('4');

    console.log(
      'PASS: BUSINESS_UNIT remains FIXED at 4 after target distribution.',
    );
  } else {
    console.log('SKIP: UI-01 allocation because Model Validation is blocked.');
  }

});
