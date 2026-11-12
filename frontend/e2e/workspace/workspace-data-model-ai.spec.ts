import { test, expect } from './workspace.fixtures';
import type { Page } from '@playwright/test';

const proposal = {
  proposal_id: 'proposal-ai-e2e-001',
  name: 'FORGE AI Order-to-Cash',
  description: 'SAP order processing, delivery, billing, and customer data.',
  suggested_tags: ['SAP', 'ERP', 'Order-to-Cash'],
  reasoning: 'The proposal covers the main entities and business process.',
};

async function mockCapabilities(
  page: Page,
  available = true,
): Promise<void> {
  await page.route('**/api/v1/ai/capabilities', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      json: {
        available,
        provider: 'ollama',
        mode: 'local',
        model: available ? 'gpt-oss:20b' : null,
        message: available
          ? 'FORGE AI is available.'
          : 'FORGE AI is unavailable for this environment.',
      },
    }),
  );
}

async function openCreateDialog(page: Page) {
  await page.goto('/workspace');
  await expect(page.locator('app-workspace')).toBeVisible();

  await page.locator('.create-dataModel-card').click();

  const dialog = page.getByRole('dialog', {
    name: 'New Data Model',
  });

  await expect(dialog).toBeVisible();
  return dialog;
}

async function deleteCreatedModel(
  page: Page,
  modelName: string,
): Promise<void> {
  await page.goto('/workspace');
  await expect(page.locator('app-workspace')).toBeVisible();

  const card = page.locator('.dataModel-card').filter({
    has: page.getByRole('heading', {
      name: modelName,
      exact: true,
    }),
  });

  if (await card.count() !== 1) {
    return;
  }

  await card.getByRole('button', {
    name: 'Edit Data Model',
  }).click();

  const dialog = page.getByRole('dialog', {
    name: 'Edit Data Model',
  });

  await dialog.locator('button.delete-button').click();

  const confirmation = page.getByRole('dialog', {
    name: 'Delete this Data Model?',
  });

  await confirmation.locator('button.confirm-button').click();
  await expect(card).toHaveCount(0, { timeout: 30_000 });
}

test.describe('WS04 - Workspace Data Model AI Assistance', () => {
  test('WS04-01: shows manual fallback when AI is unavailable', async ({
    page,
  }) => {
    await mockCapabilities(page, false);

    const dialog = await openCreateDialog(page);

    await expect(dialog).toContainText('FORGE AI unavailable');
    await expect(dialog).toContainText(
      'You can continue by defining the Data Model manually.',
    );

    await expect(page.locator('#data-model-name')).toBeVisible();
    await expect(
      dialog.getByRole('textbox', {
        name: 'Describe what you want FORGE AI to propose',
      }),
    ).toHaveCount(0);
  });

  test('WS04-02: disables empty generation and supports example selection', async ({
    page,
  }) => {
    await mockCapabilities(page, true);

    const dialog = await openCreateDialog(page);

    const prompt = dialog.getByRole('textbox', {
      name: 'Describe what you want FORGE AI to propose',
    });

    const generateButton = dialog.getByRole('button', {
      name: 'Generate Data Model',
    });

    await expect(prompt).toBeEnabled();
    await expect(generateButton).toBeDisabled();

    await dialog.getByRole('button', {
      name: 'Select',
    }).first().click();

    await expect(prompt).not.toHaveValue('');
    await expect(generateButton).toBeEnabled();
  });

  test('WS04-03: generates and displays the complete proposal', async ({
    page,
  }) => {
    await mockCapabilities(page, true);

    let requestBody: Record<string, unknown> | undefined;

    await page.route('**/api/v1/ai/data-models/suggest', async (route) => {
      requestBody = route.request().postDataJSON();

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        json: proposal,
      });
    });

    const dialog = await openCreateDialog(page);

    const prompt = 'Create an SAP Order-to-Cash data model';

    await dialog.getByRole('textbox', {
      name: 'Describe what you want FORGE AI to propose',
    }).fill(prompt);

    await dialog.getByRole('button', {
      name: 'Generate Data Model',
    }).click();

    const result = dialog.locator('.data-model-ai-proposal');

    await expect(result).toBeVisible();
    await expect(result).toContainText(proposal.name);
    await expect(result).toContainText(proposal.description);
    await expect(result).toContainText(proposal.reasoning);
    await expect(result.locator('.data-model-proposal-tag')).toHaveText(
      proposal.suggested_tags,
    );

    expect(requestBody).toEqual({
      prompt,
      regenerate: false,
    });
  });

  test('WS04-04: regenerates the proposal using the original prompt', async ({
    page,
  }) => {
    await mockCapabilities(page, true);

    const requestBodies: Record<string, unknown>[] = [];

    await page.route('**/api/v1/ai/data-models/suggest', async (route) => {
      const body = route.request().postDataJSON();
      requestBodies.push(body);

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        json: {
          ...proposal,
          name: body.regenerate
            ? 'FORGE AI Order-to-Cash Revised'
            : proposal.name,
        },
      });
    });

    const dialog = await openCreateDialog(page);
    const prompt = 'Create an SAP Order-to-Cash data model';

    await dialog.getByRole('textbox', {
      name: 'Describe what you want FORGE AI to propose',
    }).fill(prompt);

    await dialog.getByRole('button', {
      name: 'Generate Data Model',
    }).click();

    const result = dialog.locator('.data-model-ai-proposal');
    await expect(result).toContainText(proposal.name);

    await result.getByRole('button', {
      name: 'Regenerate',
    }).click();

    await expect(result).toContainText(
      'FORGE AI Order-to-Cash Revised',
    );

    expect(requestBodies).toEqual([
      { prompt, regenerate: false },
      { prompt, regenerate: true },
    ]);
  });

  test('WS04-05: displays generation errors and allows retry', async ({
    page,
  }) => {
    await mockCapabilities(page, true);

    let attempts = 0;

    await page.route('**/api/v1/ai/data-models/suggest', async (route) => {
      attempts += 1;

      if (attempts === 1) {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          json: { detail: 'AI generation failed' },
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        json: proposal,
      });
    });

    const dialog = await openCreateDialog(page);

    await dialog.getByRole('textbox', {
      name: 'Describe what you want FORGE AI to propose',
    }).fill('Create a customer data model');

    await dialog.getByRole('button', {
      name: 'Generate Data Model',
    }).click();

    await expect(
      dialog.locator('.ai-generation-error'),
    ).toBeVisible();

    await dialog.getByRole('button', {
      name: 'Generate Data Model',
    }).click();

    await expect(
      dialog.locator('.data-model-ai-proposal'),
    ).toContainText(proposal.name);

    expect(attempts).toBe(2);
  });

  test('WS04-06: accepts a proposal and creates the Data Model', async ({
    page,
  }) => {
    const modelName = `FORGE AI E2E ${Date.now()}`;
    let acceptanceRequest: Record<string, unknown> | undefined;

    await mockCapabilities(page, true);

    await page.route('**/api/v1/ai/data-models/suggest', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        json: {
          ...proposal,
          name: modelName,
        },
      });
    });

    await page.route(
      '**/api/v1/ai/data-models/proposals/activity',
      async (route) => {
        acceptanceRequest = route.request().postDataJSON();
        await route.fulfill({ status: 204 });
      },
    );

    const dialog = await openCreateDialog(page);

    await dialog.getByRole('textbox', {
      name: 'Describe what you want FORGE AI to propose',
    }).fill('Create an SAP Order-to-Cash model');

    await dialog.getByRole('button', {
      name: 'Generate Data Model',
    }).click();

    const result = dialog.locator('.data-model-ai-proposal');
    await expect(result).toBeVisible();

    await result.getByRole('button', {
      name: 'Use this proposal',
    }).click();

    await expect(page.locator('#data-model-name')).toHaveValue(modelName);
    await expect(page.locator('#data-model-description')).toHaveValue(
      proposal.description,
    );

    await expect(dialog.locator('.tag-chip')).toContainText(
      proposal.suggested_tags,
    );

    expect(acceptanceRequest).toEqual({
      action: 'ACCEPTED',
      proposal_id: proposal.proposal_id,
    });

    try {
      await dialog.locator('button.save-button').click();

      await expect(page).toHaveURL(
        /\/workspace\/[^/]+\/model-studio$/,
        { timeout: 30_000 },
      );

      await page.goto('/workspace');

      const card = page.locator('.dataModel-card').filter({
        has: page.getByRole('heading', {
          name: modelName,
          exact: true,
        }),
      });

      await expect(card).toHaveCount(1);
      await expect(card).toContainText(proposal.description);
    } finally {
      await deleteCreatedModel(page, modelName);
    }
  });
});
