import { test, expect, Page, Locator } from './workspace.fixtures';

interface AICapabilityResponse {
  available: boolean;
  provider: string;
  mode: string;
  model: string | null;
  message: string;
}

interface DataModelSuggestionResponse {
  proposal_id: string;
  name: string;
  description: string;
  suggested_tags: string[];
  reasoning: string;
}

test.describe('Workspace Create Data Model real AI integration', () => {
  test.setTimeout(240_000);

  async function openAiDialog(page: Page): Promise<Locator> {
    await page.goto('/workspace');
    await expect(page.locator('app-workspace')).toBeVisible();

    const capabilityPromise = page.waitForResponse((response) =>
      response.url().includes('/api/v1/ai/capabilities') &&
      response.request().method() === 'GET',
    );

    await page.locator('.create-dataModel-card').click();

    const dialog = page.getByRole('dialog', {
      name: 'New Data Model',
    });

    await expect(dialog).toBeVisible();

    const capabilityResponse = await capabilityPromise;

    const capability = await capabilityResponse.json() as AICapabilityResponse;

    expect(
      capability.available,
      `FORGE AI must be available. Provider: ${capability.provider}. Message: ${capability.message}`,
    ).toBe(true);

    expect(capability.provider).toBeTruthy();
    expect(capability.model).toBeTruthy();

    return dialog;
  }

  async function readRealProposal(
    responsePromise: Promise<import('@playwright/test').Response>,
    expectedPrompt: string,
    expectedRegenerate: boolean,
  ): Promise<DataModelSuggestionResponse> {
    const response = await responsePromise;
    const responseText = await response.text();

    expect(
      response.ok(),
      `Real AI proposal request failed: HTTP ${response.status()} - ${responseText}`,
    ).toBe(true);

    expect(response.request().postDataJSON()).toEqual({
      prompt: expectedPrompt,
      regenerate: expectedRegenerate,
    });

    const result = JSON.parse(responseText) as DataModelSuggestionResponse;

    expect(result.proposal_id?.trim()).toBeTruthy();
    expect(result.name?.trim()).toBeTruthy();
    expect(result.description?.trim()).toBeTruthy();
    expect(result.reasoning?.trim()).toBeTruthy();
    expect(Array.isArray(result.suggested_tags)).toBe(true);
    expect(result.suggested_tags.length).toBeGreaterThan(0);

    return result;
  }

  function verifyPromptRelevance(
    result: DataModelSuggestionResponse,
    keywords: string[],
  ): void {
    const responseText = [
      result.name,
      result.description,
      result.reasoning,
      ...result.suggested_tags,
    ].join(' ').toLowerCase();

    const matchedKeywords = keywords.filter((keyword) =>
      responseText.includes(keyword.toLowerCase()),
    );

    expect(
      matchedKeywords.length,
      `The AI response did not sufficiently reflect the prompt. Matched: ${matchedKeywords.join(', ')}. Response: ${responseText}`,
    ).toBeGreaterThanOrEqual(2);
  }

  async function evaluateDomainPrompt(
    page: Page,
    prompt: string,
    keywords: string[],
  ): Promise<DataModelSuggestionResponse> {
    const dialog = await openAiDialog(page);

    const promptInput = dialog.getByRole('textbox', {
      name: 'Describe what you want FORGE AI to propose',
    });

    await promptInput.fill(prompt);

    const responsePromise = page.waitForResponse((response) =>
      response.url().includes('/api/v1/ai/data-models/suggest') &&
      response.request().method() === 'POST',
    );

    await dialog.getByRole('button', {
      name: 'Generate Data Model',
    }).click();

    const result = await readRealProposal(
      responsePromise,
      prompt,
      false,
    );

    verifyPromptRelevance(result, keywords);

    const proposalPanel = dialog.locator('.data-model-ai-proposal');

    await expect(proposalPanel).toBeVisible();
    await expect(proposalPanel).toContainText(result.name);
    await expect(proposalPanel).toContainText(result.description);
    await expect(proposalPanel).toContainText(result.reasoning);

    await expect(
      proposalPanel.locator('.data-model-proposal-tag'),
    ).toHaveText(result.suggested_tags);

    await dialog.getByRole('button', {
      name: 'Cancel',
      exact: true,
    }).click();

    await expect(dialog).toHaveCount(0);

    return result;
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

    await expect(card).toHaveCount(0, {
      timeout: 30_000,
    });
  }

  test('WS-AI-REAL-01: understands a custom prompt, regenerates and saves the real proposal', async ({
    page,
  }) => {
    const uniqueId = Date.now().toString();

    const prompt =
      `Create a data model for an SAP Order-to-Cash process. ` +
      `Include customer master data, sales orders, order line items, ` +
      `deliveries, invoices, and payment status. ` +
      `The proposed data model name should include FORGE AI E2E ${uniqueId}.`;

    let createdModelName: string | null = null;

    try {
      const dialog = await openAiDialog(page);

      const promptInput = dialog.getByRole('textbox', {
        name: 'Describe what you want FORGE AI to propose',
      });

      await promptInput.fill(prompt);

      const initialResponsePromise = page.waitForResponse((response) =>
        response.url().includes('/api/v1/ai/data-models/suggest') &&
        response.request().method() === 'POST',
      );

      await dialog.getByRole('button', {
        name: 'Generate Data Model',
      }).click();

      const initialProposal = await readRealProposal(
        initialResponsePromise,
        prompt,
        false,
      );

      verifyPromptRelevance(initialProposal, [
        'order',
        'customer',
        'sales',
        'delivery',
        'invoice',
        'payment',
      ]);

      const proposalPanel = dialog.locator('.data-model-ai-proposal');

      await expect(proposalPanel).toBeVisible();
      await expect(proposalPanel).toContainText(initialProposal.name);
      await expect(proposalPanel).toContainText(initialProposal.description);
      await expect(proposalPanel).toContainText(initialProposal.reasoning);

      await expect(
        proposalPanel.locator('.data-model-proposal-tag'),
      ).toHaveText(initialProposal.suggested_tags);

      const regenerateResponsePromise = page.waitForResponse((response) =>
        response.url().includes('/api/v1/ai/data-models/suggest') &&
        response.request().method() === 'POST',
      );

      await proposalPanel.getByRole('button', {
        name: 'Regenerate',
      }).click();

      const regeneratedProposal = await readRealProposal(
        regenerateResponsePromise,
        prompt,
        true,
      );

      verifyPromptRelevance(regeneratedProposal, [
        'order',
        'customer',
        'sales',
        'delivery',
        'invoice',
        'payment',
      ]);

      await expect(proposalPanel).toContainText(
        regeneratedProposal.name,
      );

      const acceptanceResponsePromise = page.waitForResponse((response) =>
        response.url().includes('/api/v1/ai/data-models/proposals/activity') &&
        response.request().method() === 'POST',
      );

      await proposalPanel.getByRole('button', {
        name: 'Use this proposal',
      }).click();

      const acceptanceResponse = await acceptanceResponsePromise;

      expect(
        acceptanceResponse.ok(),
        `Proposal acceptance failed: HTTP ${acceptanceResponse.status()}`,
      ).toBe(true);

      expect(
        acceptanceResponse.request().postDataJSON(),
      ).toEqual({
        action: 'ACCEPTED',
        proposal_id: regeneratedProposal.proposal_id,
      });

      const nameInput = page.locator('#data-model-name');
      const descriptionInput = page.locator('#data-model-description');

      await expect(nameInput).toHaveValue(regeneratedProposal.name);
      await expect(descriptionInput).toHaveValue(
        regeneratedProposal.description,
      );

      await expect(dialog.locator('.tag-chip')).toContainText(
        regeneratedProposal.suggested_tags,
      );

      // Add a test-specific suffix to guarantee safe cleanup.
      createdModelName = `${regeneratedProposal.name} E2E ${uniqueId}`;
      await nameInput.fill(createdModelName);

      await dialog.locator('button.save-button').click();

      await expect(page).toHaveURL(
        /\/workspace\/[^/]+\/model-studio$/,
        { timeout: 30_000 },
      );

      await page.goto('/workspace');

      const card = page.locator('.dataModel-card').filter({
        has: page.getByRole('heading', {
          name: createdModelName,
          exact: true,
        }),
      });

      await expect(card).toHaveCount(1);
      await expect(card).toContainText(
        regeneratedProposal.description,
      );
    } finally {
      if (createdModelName) {
        await deleteCreatedModel(page, createdModelName);
      }
    }
  });

  test('WS-AI-REAL-02: generates a real proposal from a dialog example prompt', async ({
    page,
  }) => {
    const dialog = await openAiDialog(page);

    const promptInput = dialog.getByRole('textbox', {
      name: 'Describe what you want FORGE AI to propose',
    });

    await dialog.getByRole('button', {
      name: 'Select',
    }).first().click();

    await expect(promptInput).toHaveValue(/customer|master data/i);

    const selectedPrompt = await promptInput.inputValue();
    expect(selectedPrompt.trim().length).toBeGreaterThan(0);

    const responsePromise = page.waitForResponse((response) =>
      response.url().includes('/api/v1/ai/data-models/suggest') &&
      response.request().method() === 'POST',
    );

    await dialog.getByRole('button', {
      name: 'Generate Data Model',
    }).click();

    const result = await readRealProposal(
      responsePromise,
      selectedPrompt,
      false,
    );

    verifyPromptRelevance(result, [
      'customer',
      'identity',
      'contact',
      'business',
    ]);

    const proposalPanel = dialog.locator('.data-model-ai-proposal');

    await expect(proposalPanel).toBeVisible();
    await expect(proposalPanel).toContainText(result.name);
    await expect(proposalPanel).toContainText(result.description);
    await expect(proposalPanel).toContainText(result.reasoning);

    await expect(
      proposalPanel.locator('.data-model-proposal-tag'),
    ).toHaveText(result.suggested_tags);

    // This test only evaluates the proposal. It does not create a Data Model.
    await dialog.getByRole('button', {
      name: 'Cancel',
      exact: true,
    }).click();

    await expect(dialog).toHaveCount(0);
  });

  test('WS-AI-REAL-03: understands a Sales Order business domain', async ({
    page,
  }) => {
    const prompt =
      'Create a data model for enterprise sales order management. ' +
      'Include sales order headers, order line items, customer references, ' +
      'product details, delivery status, invoicing and payment status.';

    await evaluateDomainPrompt(page, prompt, [
      'sales', 'order', 'customer', 'delivery', 'invoice', 'payment',
    ]);
  });

  test('WS-AI-REAL-04: understands a Manufacturing business domain', async ({
    page,
  }) => {
    const prompt =
      'Create a data model for manufacturing operations. ' +
      'Include products, production orders, work centers, ' +
      'material requirements and production status.';

    await evaluateDomainPrompt(page, prompt, [
      'manufacturing', 'production', 'product', 'work center', 'material',
    ]);
  });

  test('WS-AI-REAL-05: handles an ambiguous prompt without assuming an industry', async ({
    page,
  }) => {
    const prompt =
      'Create a data model for managing general internal business operations. ' +
      'Keep the proposal industry-neutral. Do not assume a specific industry, ' +
      'business process, enterprise system or technology platform.';

    const result = await evaluateDomainPrompt(page, prompt, [
      'business', 'operations', 'data', 'process',
    ]);

    const proposalText = [
      result.name,
      result.description,
      result.reasoning,
      ...result.suggested_tags,
    ].join(' ').toLowerCase();

    const unsupportedDomainTerms = [
      'patient', 'diagnosis', 'prescription', 'aircraft',
      'flight operations', 'insurance claim', 'bank account',
      'loan processing', 'automotive', 'vehicle fleet', 'sap',
    ];

    const unexpectedTerms = unsupportedDomainTerms.filter((term) =>
      proposalText.includes(term),
    );

    expect(
      unexpectedTerms,
      `Unexpected industry assumptions: ${unexpectedTerms.join(', ')}. Proposal: ${proposalText}`,
    ).toEqual([]);
  });

});
