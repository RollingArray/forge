import { test, expect, Page } from '@playwright/test';

test.describe('FORGE Model Studio guided demonstration', () => {
  test('Walk through workspace, specification import and validation', async ({
    page,
  }) => {
    test.setTimeout(240_000);

    const pause = async (message: string, _defaultSeconds = 0) => {
      const configuredSeconds = Number(
        process.env.FORGE_DEMO_PAUSE_SECONDS ?? 0,
      );
      const pauseSeconds =
        Number.isFinite(configuredSeconds) && configuredSeconds > 0
          ? configuredSeconds
          : Number.isFinite(_defaultSeconds) && _defaultSeconds > 0
            ? _defaultSeconds
            : 0;

      console.log('');
      console.log('================================================');
      console.log(`DEMO: ${message}`);

      if (pauseSeconds > 0) {
        console.log(`Pausing for ${pauseSeconds} seconds...`);
        await page.waitForTimeout(pauseSeconds * 1000);
      } else {
        console.log('No intentional pause configured.');
      }

      console.log('================================================');
    };

    const fillCsvSection = async (
      page: Page,
      sectionName: string,
      csv: string,
    ) => {
      console.log(`DEMO: Entering ${sectionName} CSV`);
      await page.getByRole('tab', {
        name: sectionName,
        exact: true,
      }).click();
      await page.locator('#csv-section-input').fill(csv);
      await pause(`${sectionName} CSV entered. Inspect the content.`, 5);
    };

    const uniqueId =
      `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const modelName = `FORGE DEMO ${uniqueId}`;
    const description = `Guided Model Studio demonstration ${uniqueId}`;

    let modelCreated = false;

    try {
      // 1. Workspace
      await page.goto('/workspace');
      await expect(page.locator('app-workspace')).toBeVisible();
      await pause('Welcome to the FORGE workspace.', 10);

      // 2. Create a dedicated demonstration model
      console.log('DEMO: Creating a new demonstration Data Model');
      await page.locator('.create-dataModel-card').click();

      const dialog = page.getByRole('dialog', {
        name: 'New Data Model',
      });
      await expect(dialog).toBeVisible();
      await pause('New Data Model dialog. We will enter the model details.', 6);

      await page.locator('#data-model-name').fill(modelName);
      await page.locator('#data-model-description').fill(description);
      await pause('Model name and description entered.', 6);

      const saveButton = dialog.locator('button.save-button');
      await expect(saveButton).toBeEnabled();
      await saveButton.click();

      await expect(page).toHaveURL(
        /\/workspace\/[^/]+\/model-studio$/,
        { timeout: 30_000 },
      );
      modelCreated = true;

      const match = page.url().match(
        /\/workspace\/([^/]+)\/model-studio$/,
      );
      if (!match) {
        throw new Error('Could not identify the newly created model.');
      }
      const modelId = match[1];

      await pause(
        'The new Data Model has been created. This is its initial Model Studio.',
        10,
      );

      // 3. Return to workspace and reopen the model
      await page.goto('/workspace');
      await expect(page.locator('app-workspace')).toBeVisible();

      const modelCard = page.locator('.dataModel-card').filter({
        has: page.getByRole('heading', {
          name: modelName,
          exact: true,
        }),
      });
      await expect(modelCard).toHaveCount(1);
      await pause(
        'The new model is visible in the workspace. We will open it.',
        7,
      );

      await modelCard.click();
      await expect(page).toHaveURL(
        new RegExp(`/workspace/${modelId}/model-studio$`),
      );
      await expect(
        page.getByRole('heading', {
          name: 'Model Studio',
          exact: true,
        }),
      ).toBeVisible();

      await pause(
        'Model Studio is open. Next we will define the enterprise data structure.',
        10,
      );

      // 4. Open CSV Specification wizard
      await page.getByRole('button', {
        name: /CSV Specification/,
      }).click();

      await expect(page).toHaveURL(
        new RegExp(`/workspace/${modelId}/specification-wizard$`),
      );
      await expect(
        page.getByRole('heading', {
          name: 'Define your Data Model',
          exact: true,
        }),
      ).toBeVisible();

      await pause(
        'CSV Specification wizard opened. It has separate sections for entities, fields, keys and relationships.',
        10,
      );

      // 5. Enter entities
      await fillCsvSection(
        page,
        'Entities',
        [
          'entity,description',
          'Customer,Customer master record',
          'Order,Customer order record',
        ].join('\n'),
      );

      // 6. Enter fields and identity keys
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

      // 7. Define the foreign key
      await fillCsvSection(
        page,
        'Foreign Keys',
        [
          'source_entity,source_fields,target_entity',
          'Order,"[""CUSTOMER_ID""]",Customer',
        ].join('\n'),
      );

      // 8. Define the business relationship
      await fillCsvSection(
        page,
        'Relationships',
        [
          'source_entity,target_entity,type',
          'Customer,Order,ONE_TO_MANY',
        ].join('\n'),
      );

      await pause(
        'The Customer and Order structures are defined, including the foreign key and one-to-many relationship.',
        10,
      );

      // 9. Preview and apply the specification
      console.log('DEMO: Previewing the CSV specification');
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

      await pause(
        'Import preview is ready. Review the validation result before applying.',
        12,
      );

      await page.getByRole('button', {
        name: /Apply additions & open Model Studio/,
      }).click();

      await expect(page).toHaveURL(
        new RegExp(`/workspace/${modelId}/model-studio$`),
        { timeout: 60_000 },
      );

      // 10. Inspect generated model structure
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

      await pause(
        'The imported model is now visible: Customer, Order and their relationship. Take a moment to inspect the canvas.',
        15,
      );

      // 11. Navigate to validation
      console.log('DEMO: Continuing to Model Validation');
      await page.getByRole('button', {
        name: 'Continue to Validation',
        exact: true,
      }).click();

      await expect(page).toHaveURL(
        new RegExp(`/workspace/${modelId}/model-validation$`),
      );
      await expect(
        page.getByRole('heading', {
          name: 'Model Validation',
          exact: true,
        }),
      ).toBeVisible();

      await pause(
        'Model Validation is open. This is where the model can be reviewed before population planning.',
        15,
      );

      // 12. Return to Model Studio
      await page.getByRole('button', {
        name: 'Back to Model',
        exact: true,
      }).click();

      await expect(page).toHaveURL(
        new RegExp(`/workspace/${modelId}/model-studio$`),
      );
      await expect(entityNodes).toHaveCount(2);

      await pause(
        'We have returned to Model Studio. The two entities and their relationship are still present.',
        15,
      );

      console.log('');
      console.log('FORGE MODEL STUDIO DEMONSTRATION COMPLETED SUCCESSFULLY.');
      console.log(`Demonstration model: ${modelName}`);
      await pause(
        'Final inspection. The demonstration model will be cleaned up after this pause.',
        20,
      );
    } finally {
      // Delete only the uniquely named model created by this demonstration.
      if (modelCreated) {
        console.log('DEMO CLEANUP: Removing the demonstration model.');
        await page.goto('/workspace');
        await expect(page.locator('app-workspace')).toBeVisible();

        const ownedCard = page.locator('.dataModel-card').filter({
          has: page.getByRole('heading', {
            name: modelName,
            exact: true,
          }),
        });

        if (await ownedCard.count() === 1) {
          await ownedCard.getByRole('button', {
            name: 'Edit Data Model',
          }).click();

          const editDialog = page.getByRole('dialog', {
            name: 'Edit Data Model',
          });
          await expect(editDialog).toBeVisible();
          await editDialog.locator('button.delete-button').click();

          const confirmation = page.getByRole('dialog', {
            name: 'Delete this Data Model?',
          });
          await expect(confirmation).toBeVisible();
          await expect(confirmation).toContainText(modelName);
          await confirmation.locator('button.confirm-button').click();

          await expect(ownedCard).toHaveCount(0, {
            timeout: 30_000,
          });
          console.log('DEMO CLEANUP: Demonstration model deleted.');
        } else {
          console.log(
            'DEMO CLEANUP: Model was not found uniquely. No deletion performed.',
          );
        }
      }
    }
  });
});
