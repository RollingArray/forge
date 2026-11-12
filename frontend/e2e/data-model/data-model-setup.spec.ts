import { test, expect } from '../workspace/workspace.fixtures';

test.describe('DM01 - Data Model Setup', () => {
  test('DM01-01: imports Aerospace specification, validates the model and verifies population planning', async ({
    page,
    workspaceModel,
  }, testInfo) => {
    test.setTimeout(180_000);
    let modelId = '';
    let canContinue = false;

    await test.step('DM01-S01: Open test-owned Data Model', async () => {
      // --------------------------------------------------
      // 1. Open the test-owned Data Model in Model Studio
      // --------------------------------------------------

      await workspaceModel.card.click();

      await expect(page).toHaveURL(/\/workspace\/[^/]+\/model-studio$/);

      const modelStudioUrl = new URL(page.url());
      modelId = modelStudioUrl.pathname.split('/')[2];

      expect(modelId).toBeTruthy();

      await testInfo.attach('created-data-model', {
        body: JSON.stringify(
          {
            name: workspaceModel.name,
            dataModelId: modelId,
            modelStudioUrl: page.url(),
          },
          null,
          2,
        ),
        contentType: 'application/json',
      });
    });

    await test.step('DM01-S02: Open CSV Specification Wizard', async () => {
      // --------------------------------------------------
      // 2. Open CSV Specification Wizard
      // --------------------------------------------------

      await page
        .getByRole('button', {
          name: /CSV Specification/,
        })
        .click();

      await expect(page).toHaveURL(new RegExp(`/workspace/${modelId}/specification-wizard`));

      await expect(page.getByRole('heading', { name: 'Define your Data Model' })).toBeVisible();
    });

    await test.step('DM01-S03: Load and verify Aerospace CSV sections', async () => {
      // --------------------------------------------------
      // 3. Load and verify all five Aerospace CSV sections
      // --------------------------------------------------

      await page
        .getByRole('button', {
          name: 'Load Complete Aerospace Sample',
        })
        .click();

      const sections = [
        {
          name: 'Entities',
          header: 'entity,description,population_count,population_scaling',
        },
        {
          name: 'Fields & Keys',
          header:
            'entity,field,type,identity_position,identity_strategy,generation_strategy,distribution,generator,minimum,maximum,minimum_length,maximum_length,character_set,pattern,semantic_description,semantic_mode,values',
        },
        {
          name: 'Foreign Keys',
          header: 'source_entity,source_fields,target_entity',
        },
        {
          name: 'Relationships',
          header: 'source_entity,target_entity,type,source_participation,target_participation',
        },
        {
          name: 'Constraints',
          header: 'entity,field,operator,value',
        },
      ];

      const escapeRegex = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

      const textarea = page.locator('#csv-section-input');

      for (const section of sections) {
        const tab = page.getByRole('tab', {
          name: section.name,
          exact: true,
        });

        await expect(tab).toBeVisible();
        await tab.click();

        await expect(textarea).toHaveValue(new RegExp(`^${escapeRegex(section.header)}`));
      }
    });

    await test.step('DM01-S04: Preview and apply specification import', async () => {
      // --------------------------------------------------
      // 4. Preview and apply the specification import
      // --------------------------------------------------

      await page
        .getByRole('button', {
          name: /^Preview CSV import$/,
        })
        .click();

      const review = page.locator('section[aria-label="CSV import review"]');

      await expect(review).toBeVisible();

      await expect(review.getByText('Ready to apply', { exact: true })).toBeVisible({
        timeout: 60_000,
      });

      await page
        .getByRole('button', {
          name: /Apply additions & open Model Studio/,
        })
        .click();

      await expect(page).toHaveURL(new RegExp(`/workspace/${modelId}/model-studio`), {
        timeout: 60_000,
      });
    });

    await test.step('DM01-S05: Validate Data Model', async () => {
      // --------------------------------------------------
      // 5. Model Validation UI acceptance
      // --------------------------------------------------

      await page
        .getByRole('button', {
          name: 'Continue to Validation',
          exact: true,
        })
        .click();

      await expect(page).toHaveURL(new RegExp(`/workspace/${modelId}/model-validation$`));

      const validationReady = page.getByText('Ready for Population', { exact: true });

      const validationBlocked = page.getByText('Requires Attention', { exact: true });

      await expect(validationReady.or(validationBlocked)).toBeVisible({ timeout: 60_000 });

      canContinue = await validationReady.isVisible();

      await page.screenshot({
        path: testInfo.outputPath('wp02-model-validation.png'),
        fullPage: true,
      });
    });

    await test.step('DM01-S06: Verify Population Plan', async () => {
      // --------------------------------------------------
      // 6. Population Plan UI acceptance
      // --------------------------------------------------

      await page
        .getByRole('button', {
          name: 'Population Plan',
          exact: true,
        })
        .click();

      await expect(page).toHaveURL(new RegExp(`/workspace/${modelId}/data-model/population$`));

      await expect(
        page.getByRole('heading', {
          name: 'Population Plan',
          exact: true,
        }),
      ).toBeVisible();

      if (!canContinue) {
        await expect(page.getByText('POPULATION PLAN BLOCKED', { exact: true })).toBeVisible({
          timeout: 60_000,
        });
      } else {
        await expect(page.getByText('Entity Population Plan', { exact: true })).toBeVisible({
          timeout: 60_000,
        });

        await expect(page.locator('#population-target')).toBeVisible();

        await page.screenshot({
          path: testInfo.outputPath('wp02-population-plan.png'),
          fullPage: true,
        });
      }
    });

    if (canContinue) {
      await test.step('DM01-S07: Execute population allocation', async () => {
        // --------------------------------------------------
        // 7. Standard population allocation
        // --------------------------------------------------

        const targetInput = page.locator('#population-target');

        await targetInput.fill('1000');

        await page.locator('.population-target-button').click();

        const candidateHeading = page.locator('.candidate-decision-header strong');

        await expect(candidateHeading).toBeVisible({
          timeout: 60_000,
        });

        const candidateDecision = await candidateHeading.innerText();

        await testInfo.attach('population-candidate-decision', {
          body: candidateDecision,
          contentType: 'text/plain',
        });

        await page.screenshot({
          path: testInfo.outputPath('wp02-population-candidate.png'),
          fullPage: true,
        });
      });

      await test.step('DM01-S08: Verify fixed BUSINESS_UNIT population', async () => {
        // --------------------------------------------------
        // 8. Verify fixed BUSINESS_UNIT population
        // --------------------------------------------------

        const businessUnitRow = page
          .locator('.simple-table-row')
          .filter({ hasText: 'BUSINESS_UNIT' });

        await expect(businessUnitRow).toHaveCount(1);

        await expect(businessUnitRow.locator('.mode-badge')).toHaveText('FIXED');

        // Current population: column 5 in the rendered table.
        await expect(businessUnitRow.locator(':scope > span').nth(4)).toHaveText('4');

        // Proposed and planned populations remain fixed at four.
        await expect(businessUnitRow.locator('.numeric-cell').nth(1)).toHaveText('4');

        await expect(businessUnitRow.locator('.numeric-cell').nth(2)).toHaveText('4');
      });
    }
  });
});
