import { test, expect } from './workspace.fixtures';

test.describe('WS03 - Workspace Data Model Dialog', () => {
  test('WS03-01: prevents saving an empty or whitespace-only name', async ({
    page,
  }) => {
    await page.goto('/workspace');
    await page.locator('.create-dataModel-card').click();

    const dialog = page.getByRole('dialog', {
      name: 'New Data Model',
    });

    await expect(dialog).toBeVisible();

    const saveButton = dialog.locator('button.save-button');

    await expect(saveButton).toBeDisabled();

    await page.locator('#data-model-name').fill('   ');
    await expect(saveButton).toBeDisabled();

    await dialog.getByRole('button', {
      name: 'Cancel',
      exact: true,
    }).click();

    await expect(dialog).toHaveCount(0);
  });

  test('WS03-02: trims name and description when saving edits', async ({
    page,
    workspaceModel,
  }) => {
    await workspaceModel.card.getByRole('button', {
      name: 'Edit Data Model',
    }).click();

    const dialog = page.getByRole('dialog', {
      name: 'Edit Data Model',
    });

    await page.locator('#data-model-name').fill(`  ${workspaceModel.name} Updated  `);
    await page.locator('#data-model-description').fill('  Updated description  ');
    await dialog.locator('button.save-button').click();

    // Update fixture identity immediately after the save succeeds.
    workspaceModel.name = `${workspaceModel.name} Updated`;
    workspaceModel.description = 'Updated description';

    await expect(dialog).toHaveCount(0);
    await expect(page).toHaveURL(/\/workspace\/?$/);

    const updatedCard = page.locator('.dataModel-card').filter({
      has: page.getByRole('heading', {
        name: workspaceModel.name,
        exact: true,
      }),
    });

    await expect(updatedCard).toHaveCount(1);
    await expect(updatedCard).toContainText('Updated description');
  });

  test('WS03-03: trims tags and removes case-insensitive duplicates', async ({
    page,
    workspaceModel,
  }) => {
    await workspaceModel.card.getByRole('button', {
      name: 'Edit Data Model',
    }).click();

    const dialog = page.getByRole('dialog', {
      name: 'Edit Data Model',
    });

    const tagInput = dialog.getByRole('textbox', {
      name: 'Add tag',
    });

    await tagInput.fill(' SAP, sap, Manufacturing , ERP ');
    await tagInput.press('Enter');

    await expect(dialog.locator('.tag-chip')).toHaveCount(3);
    await expect(dialog.locator('.tag-chip')).toContainText([
      'SAP',
      'Manufacturing',
      'ERP',
    ]);

    await dialog.locator('button.save-button').click();

    const card = page.locator('.dataModel-card').filter({
      has: page.getByRole('heading', {
        name: workspaceModel.name,
        exact: true,
      }),
    });

    await expect(card.locator('.dataModel-tag')).toHaveText([
      'SAP',
      'Manufacturing',
      'ERP',
    ]);
  });

  test('WS03-04: displays no more than four tags and an overflow count', async ({
    page,
    workspaceModel,
  }) => {
    await workspaceModel.card.getByRole('button', {
      name: 'Edit Data Model',
    }).click();

    const dialog = page.getByRole('dialog', {
      name: 'Edit Data Model',
    });

    await dialog.getByRole('textbox', {
      name: 'Add tag',
    }).fill('one, two, three, four, five, six');

    await dialog.getByRole('textbox', {
      name: 'Add tag',
    }).press('Enter');

    await dialog.locator('button.save-button').click();

    const card = page.locator('.dataModel-card').filter({
      has: page.getByRole('heading', {
        name: workspaceModel.name,
        exact: true,
      }),
    });

    await expect(card.locator('.dataModel-tag')).toHaveCount(4);
    await expect(card.locator('.dataModel-tag-more')).toHaveText('+2');
  });

  test('WS03-05: selects and persists a color', async ({
    page,
    workspaceModel,
  }) => {
    await workspaceModel.card.getByRole('button', {
      name: 'Edit Data Model',
    }).click();

    const dialog = page.getByRole('dialog', {
      name: 'Edit Data Model',
    });

    const colorOption = dialog.getByRole('radio', {
      name: /^Select color /,
    }).nth(0);

    const selectedColorLabel = await colorOption.getAttribute('aria-label');
    expect(selectedColorLabel).toBeTruthy();

    const selectedColor = selectedColorLabel!.replace(
      'Select color ',
      '',
    );

    await colorOption.click();
    await expect(colorOption).toHaveAttribute('aria-checked', 'true');

    await dialog.locator('button.save-button').click();
    await expect(dialog).toHaveCount(0);

    const card = page.locator('.dataModel-card').filter({
      has: page.getByRole('heading', {
        name: workspaceModel.name,
        exact: true,
      }),
    });

    await expect(card).toHaveCount(1);

    const persistedColor = await card.evaluate((element) =>
      getComputedStyle(element)
        .getPropertyValue('--data-model-color')
        .trim(),
    );

    expect(persistedColor.toLowerCase()).toBe(selectedColor.toLowerCase());
  });

  test('WS03-06: cancelling an edit leaves the model unchanged', async ({
    page,
    workspaceModel,
  }) => {
    await workspaceModel.card.getByRole('button', {
      name: 'Edit Data Model',
    }).click();

    await page.locator('#data-model-name').fill('Unsaved Workspace Change');

    await page.getByRole('dialog', {
      name: 'Edit Data Model',
    }).getByRole('button', {
      name: 'Cancel',
      exact: true,
    }).click();

    await expect(page.getByRole('dialog')).toHaveCount(0);

    await expect(
      page.getByRole('heading', {
        name: workspaceModel.name,
        exact: true,
      }),
    ).toBeVisible();

    await expect(
      page.getByRole('heading', {
        name: 'Unsaved Workspace Change',
        exact: true,
      }),
    ).toHaveCount(0);
  });

  test('WS03-07: cancelling delete confirmation preserves the model', async ({
    page,
    workspaceModel,
  }) => {
    await workspaceModel.card.getByRole('button', {
      name: 'Edit Data Model',
    }).click();

    const editDialog = page.getByRole('dialog', {
      name: 'Edit Data Model',
    });

    await editDialog.locator('button.delete-button').click();

    const confirmation = page.getByRole('dialog', {
      name: 'Delete this Data Model?',
    });

    await expect(confirmation).toBeVisible();
    await expect(confirmation).toContainText(workspaceModel.name);

    await confirmation.locator('button.cancel-button').click();

    await expect(confirmation).toHaveCount(0);
    await expect(editDialog).toBeVisible();
    await expect(page.locator('#data-model-name')).toHaveValue(
      workspaceModel.name,
    );
  });

  test('WS03-08: confirms deletion through the UI', async ({
    page,
    workspaceModel,
  }) => {
    await workspaceModel.card.getByRole('button', {
      name: 'Edit Data Model',
    }).click();

    await page.getByRole('dialog', {
      name: 'Edit Data Model',
    }).locator('button.delete-button').click();

    const confirmation = page.getByRole('dialog', {
      name: 'Delete this Data Model?',
    });

    await expect(confirmation).toBeVisible();
    await expect(confirmation).toContainText(workspaceModel.name);

    await confirmation.locator('button.confirm-button').click();

    await expect(
      page.locator('.dataModel-card').filter({
        has: page.getByRole('heading', {
          name: workspaceModel.name,
          exact: true,
        }),
      }),
    ).toHaveCount(0, { timeout: 30_000 });

    workspaceModel.deletedByTest = true;
  });

  test('WS03-09: persists edited model details after page reload', async ({
    page,
    workspaceModel,
  }) => {
    const updatedName = `${workspaceModel.name} Persisted`;
    const updatedDescription = 'Persistence verification description';
    const expectedTags = ['Persistence', 'Regression', 'Workspace'];

    await workspaceModel.card.getByRole('button', {
      name: 'Edit Data Model',
    }).click();

    const dialog = page.getByRole('dialog', {
      name: 'Edit Data Model',
    });

    await page.locator('#data-model-name').fill(`  ${updatedName}  `);
    await page.locator('#data-model-description').fill(
      `  ${updatedDescription}  `,
    );

    const tagInput = dialog.getByRole('textbox', {
      name: 'Add tag',
    });

    await tagInput.fill(expectedTags.join(', '));
    await tagInput.press('Enter');

    const colorOption = dialog.getByRole('radio', {
      name: /^Select color /,
    }).nth(0);

    const colorLabel = await colorOption.getAttribute('aria-label');
    expect(colorLabel).toBeTruthy();

    const expectedColor = colorLabel!.replace('Select color ', '');
    await colorOption.click();
    await expect(colorOption).toHaveAttribute('aria-checked', 'true');

    await dialog.locator('button.save-button').click();
    await expect(dialog).toHaveCount(0);

    workspaceModel.name = updatedName;
    workspaceModel.description = updatedDescription;

    await page.reload();
    await expect(page.locator('app-workspace')).toBeVisible();

    const persistedCard = page.locator('.dataModel-card').filter({
      has: page.getByRole('heading', {
        name: updatedName,
        exact: true,
      }),
    });

    await expect(persistedCard).toHaveCount(1);
    await expect(persistedCard).toContainText(updatedDescription);
    await expect(persistedCard.locator('.dataModel-tag')).toHaveText(
      expectedTags,
    );

    const persistedColor = await persistedCard.evaluate((element) =>
      getComputedStyle(element)
        .getPropertyValue('--data-model-color')
        .trim(),
    );

    expect(persistedColor.toLowerCase()).toBe(expectedColor.toLowerCase());
  });

});
