import { test, expect } from './model-studio.fixtures';

test.describe('MS06 - Field editing', () => {
  test.describe.configure({ timeout: 120_000 });

  const fieldName = 'CUSTOMER_NAME';

  function fieldUpdatePath(modelId: string, entityName = 'Customer') {
    return `/data-models/${modelId}/specification/entities/${encodeURIComponent(entityName)}/fields/${encodeURIComponent(fieldName)}`;
  }

  async function openExistingField(
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

    const fieldRow = inspector.locator('app-inspector-row')
      .filter({ hasText: fieldName });

    await expect(fieldRow).toHaveCount(1);

    await fieldRow.locator('button.inspector-row-edit').click();

    const dialog = page.getByRole('dialog', {
      name: 'Edit Field',
      exact: true,
    });

    await expect(dialog).toBeVisible();

    return { inspector, fieldRow, dialog };
  }

  function choiceButton(
    dialog: import('@playwright/test').Locator,
    title: string,
  ) {
    return dialog.locator(
      `app-choice-card:has(strong:text-is("${title}")) button.choice-card`,
    );
  }

  test('MS06-01: Open existing field', async ({
    page,
    populatedModelStudio,
  }) => {
    await expect(page).toHaveURL(
      new RegExp(`/workspace/${populatedModelStudio.id}/model-studio$`),
    );

    const { dialog } = await openExistingField(page);

    await expect(dialog.locator('#field-name')).toHaveValue(fieldName);
    await expect(dialog.locator('#field-name')).toHaveAttribute('readonly', '');

    await expect(choiceButton(dialog, 'Text')).toHaveClass(/selected/);
    await expect(choiceButton(dialog, 'Random Text')).toHaveClass(/selected/);
    await expect(choiceButton(dialog, 'Letters and numbers')).toHaveClass(/selected/);

    await expect(dialog.locator('#minimum-length')).toHaveValue('8');
    await expect(dialog.locator('#maximum-length')).toHaveValue('40');

    await expect(dialog.locator('.save-button')).toBeVisible();
    await expect(dialog.locator('.cancel-button')).toBeVisible();
  });

  test('MS06-02: Edit permitted field properties', async ({
    page,
    populatedModelStudio,
  }) => {
    const { dialog } = await openExistingField(page);

    await dialog.locator('#minimum-length').fill('10');
    await dialog.locator('#maximum-length').fill('32');

    const updateResponsePromise = page.waitForResponse((response) => {
      const request = response.request();
      const pathname = new URL(response.url()).pathname;

      return (
        request.method() === 'PUT' &&
        pathname.endsWith(fieldUpdatePath(populatedModelStudio.id))
      );
    });

    await dialog.locator('.save-button').click();

    const updateResponse = await updateResponsePromise;
    const responseBody = await updateResponse.text();

    expect(
      updateResponse.status(),
      `Field update should return HTTP 200. API response: ${responseBody}`,
    ).toBe(200);

    const updatedField = JSON.parse(responseBody);

    expect(updatedField.name).toBe(fieldName);
    expect(updatedField.type).toBe('STRING');
    expect(updatedField.generation.generator).toBe('RANDOM_STRING');
    expect(updatedField.generation.parameters).toMatchObject({
      minimum_length: 10,
      maximum_length: 32,
      character_set: 'ALPHANUMERIC',
    });

    await expect(dialog).toBeHidden();
  });

  test('MS06-03: Verify locked configuration options', async ({
    page,
    populatedModelStudio,
  }) => {
    const { dialog } = await openExistingField(page);

    await expect(dialog.locator('#field-name'))
      .toHaveAttribute('readonly', '');
    await expect(dialog.locator('#minimum-length')).toBeEnabled();
    await expect(dialog.locator('#maximum-length')).toBeEnabled();

    const lockedChoices = [
      'Unique ID',
      'Text',
      'Whole Number',
      'Decimal Number',
      'Yes / No',
      'Choice / Category',
      'Random Text',
      'Pattern',
      'Meaningful Text',
      'Letters only',
      'Numbers only',
      'Letters and numbers',
    ];

    for (const title of lockedChoices) {
      await expect(choiceButton(dialog, title)).toBeDisabled();
    }

    // Locked choices must remain unchanged when a user attempts to select them.
    await expect(choiceButton(dialog, 'Text')).toHaveClass(/selected/);
    await expect(choiceButton(dialog, 'Random Text')).toHaveClass(/selected/);
    await expect(choiceButton(dialog, 'Letters and numbers')).toHaveClass(/selected/);

    await dialog.locator('#minimum-length').fill('9');
    await expect(dialog.locator('#minimum-length')).toHaveValue('9');

    await dialog.locator('.cancel-button').click();
    await expect(dialog).toBeHidden();
  });

  test('MS06-04: Cancel field editing', async ({
    page,
    populatedModelStudio,
  }) => {
    const { dialog } = await openExistingField(page);

    let updateRequests = 0;
    const expectedPath = fieldUpdatePath(populatedModelStudio.id);

    page.on('request', (request) => {
      const pathname = new URL(request.url()).pathname;

      if (
        request.method() === 'PUT' &&
        pathname.endsWith(expectedPath)
      ) {
        updateRequests += 1;
      }
    });

    await dialog.locator('#minimum-length').fill('12');
    await dialog.locator('#maximum-length').fill('30');
    await dialog.locator('.cancel-button').click();

    await expect(dialog).toBeHidden();

    expect(
      updateRequests,
      'Cancelling field editing should not issue an update request',
    ).toBe(0);

    const reopened = await openExistingField(page);

    await expect(reopened.dialog.locator('#minimum-length')).toHaveValue('8');
    await expect(reopened.dialog.locator('#maximum-length')).toHaveValue('40');
  });

  test('MS06-05: Reload after editing', async ({
    page,
    populatedModelStudio,
  }) => {
    const { dialog } = await openExistingField(page);

    await dialog.locator('#minimum-length').fill('11');
    await dialog.locator('#maximum-length').fill('36');

    const updateResponsePromise = page.waitForResponse((response) => {
      const request = response.request();
      const pathname = new URL(response.url()).pathname;

      return (
        request.method() === 'PUT' &&
        pathname.endsWith(fieldUpdatePath(populatedModelStudio.id))
      );
    });

    await dialog.locator('.save-button').click();

    const updateResponse = await updateResponsePromise;
    const responseBody = await updateResponse.text();

    expect(
      updateResponse.status(),
      `Field update should return HTTP 200. API response: ${responseBody}`,
    ).toBe(200);

    await expect(dialog).toBeHidden();

    await page.reload();

    const reopened = await openExistingField(page);

    await expect(reopened.dialog.locator('#field-name')).toHaveValue(fieldName);
    await expect(reopened.dialog.locator('#minimum-length')).toHaveValue('11');
    await expect(reopened.dialog.locator('#maximum-length')).toHaveValue('36');
    await expect(choiceButton(reopened.dialog, 'Text')).toHaveClass(/selected/);
    await expect(choiceButton(reopened.dialog, 'Random Text')).toHaveClass(/selected/);
    await expect(choiceButton(reopened.dialog, 'Letters and numbers')).toHaveClass(/selected/);
  });
});
