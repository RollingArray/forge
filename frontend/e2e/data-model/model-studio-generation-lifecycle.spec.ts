import {
  test,
  expect,
  Browser,
  BrowserContext,
  Page,
  TestInfo,
} from '@playwright/test';
import { randomUUID } from 'node:crypto';
import path from 'node:path';

const ENTITY = 'TestRecord';
const TARGET_ROWS = 12;
const BASE_URL = process.env.FORGE_E2E_BASE_URL ?? 'http://127.0.0.1:18876';
const AUTH_FILE = path.resolve(
  __dirname,
  '../../playwright/.auth/isolated-owner.json',
);

interface Scenario {
  modelId: string;
  modelName: string;
}

interface GenerationJob {
  data_model_id: string;
  job_id: string;
  status: string;
  total_target_rows: number;
  total_generated_rows: number;
  progress: number;
}

let setupContext: BrowserContext | undefined;
let scenario: Scenario | undefined;
let createdModelName: string | undefined;

function requireScenario(): Scenario {
  if (!scenario) {
    throw new Error('MS30 shared generation scenario was not initialized.');
  }
  return scenario;
}

function generationUrl(modelId: string, jobId?: string): string {
  const base = `/workspace/${modelId}/data-model/generate`;
  return jobId ? `${base}/${jobId}` : base;
}

async function getApiAuthorizationHeaders(
  page: Page,
): Promise<Record<string, string>> {
  const session = await page.evaluate(() => {
    const stored = localStorage.getItem('forge.auth.session');
    if (!stored) return null;

    try {
      const parsed = JSON.parse(stored);
      return {
        accessToken: parsed.accessToken,
        tokenType: parsed.tokenType,
      };
    } catch {
      return null;
    }
  });

  expect(
    session?.accessToken,
    'Authenticated E2E session should contain an access token',
  ).toBeTruthy();
  expect(session?.tokenType).toBe('Bearer');

  return {
    Authorization: `${session!.tokenType} ${session!.accessToken}`,
  };
}

async function getGenerationJob(
  page: Page,
  modelId: string,
  jobId: string,
): Promise<GenerationJob> {
  const origin = new URL(page.url()).origin;
  const response = await page.context().request.get(
    `${origin}/api/v1/data-models/${modelId}/generation/${jobId}`,
    { headers: await getApiAuthorizationHeaders(page) },
  );

  expect(response.status()).toBe(200);
  return await response.json() as GenerationJob;
}

async function listGenerationJobs(
  page: Page,
  modelId: string,
): Promise<GenerationJob[]> {
  const origin = new URL(page.url()).origin;
  const response = await page.context().request.get(
    `${origin}/api/v1/data-models/${modelId}/generation`,
    { headers: await getApiAuthorizationHeaders(page) },
  );

  expect(response.status()).toBe(200);
  return await response.json() as GenerationJob[];
}

async function createGenerationJob(
  page: Page,
  modelId: string,
): Promise<GenerationJob> {
  const origin = new URL(page.url()).origin;
  const response = await page.context().request.post(
    `${origin}/api/v1/data-models/${modelId}/generation`,
    {
      headers: await getApiAuthorizationHeaders(page),
      data: {},
    },
  );

  expect(
    response.status(),
    `Generation job creation failed: ${await response.text()}`,
  ).toBe(201);

  return await response.json() as GenerationJob;
}

async function createScenarioModel(page: Page): Promise<Scenario> {
  const uniqueId = `${Date.now()}-${randomUUID().slice(0, 8)}`;
  const modelName = `FORGE MS30 E2E ${uniqueId}`;

  await page.goto('/workspace');
  await expect(page.locator('app-workspace')).toBeVisible();

  await page.locator('.create-dataModel-card').click();

  const dialog = page.getByRole('dialog', { name: 'New Data Model' });
  await expect(dialog).toBeVisible();
  await page.locator('#data-model-name').fill(modelName);
  await page.locator('#data-model-description').fill(
    `MS30 generation lifecycle scenarios ${uniqueId}`,
  );

  const saveButton = dialog.locator('button.save-button');
  await expect(saveButton).toBeEnabled();
  await saveButton.click();

  await expect(page).toHaveURL(
    /\/workspace\/[^/]+\/model-studio$/,
    { timeout: 30_000 },
  );

  const match = page.url().match(/\/workspace\/([^/]+)\/model-studio$/);
  expect(match, 'Expected model ID in Model Studio URL').not.toBeNull();

  return {
    modelId: match![1],
    modelName,
  };
}

async function importGenerationSpecification(
  page: Page,
  modelId: string,
): Promise<void> {
  await page.getByRole('button', { name: /CSV Specification/ }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelId}/specification-wizard$`),
  );

  await page.getByRole('tab', {
    name: 'Entities',
    exact: true,
  }).click();

  await page.locator('#csv-section-input').fill([
    'entity,description,population_count,population_scaling',
    `${ENTITY},MS30 generation lifecycle test entity,${TARGET_ROWS},FIXED`,
  ].join('\n'));

  await page.getByRole('tab', {
    name: 'Fields & Keys',
    exact: true,
  }).click();

  await page.locator('#csv-section-input').fill([
    [
      'entity', 'field', 'type', 'identity_position',
      'identity_strategy', 'generation_strategy', 'distribution',
      'generator', 'minimum', 'maximum', 'minimum_length',
      'maximum_length', 'character_set', 'pattern',
      'semantic_description', 'semantic_mode', 'values',
    ].join(','),
    [
      ENTITY, 'RECORD_ID', 'IDENTIFIER', '1',
      'SEQUENTIAL_ID', '', '', '', '', '', '', '', '', '', '', '', '',
    ].join(','),
  ].join('\n'));

  const emptySections: Record<string, string> = {
    'Foreign Keys': 'source_entity,source_fields,target_entity',
    Relationships:
      'source_entity,target_entity,type,source_participation,target_participation',
    Constraints: 'entity,field,operator,value',
  };

  for (const [section, csv] of Object.entries(emptySections)) {
    await page.getByRole('tab', {
      name: section,
      exact: true,
    }).click();
    await page.locator('#csv-section-input').fill(csv);
  }

  await page.getByRole('button', {
    name: /^Prepare replacement$/,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelId}/model-validation$`),
    { timeout: 60_000 },
  );

  await expect(
    page.getByRole('heading', {
      name: 'Model Validation',
      exact: true,
    }),
  ).toBeVisible();

  const confirmButton = page.getByRole('button', {
    name: 'Confirm replacement',
    exact: true,
  });

  await expect(confirmButton).toBeEnabled({ timeout: 60_000 });

  page.once('dialog', async (dialog) => {
    await dialog.accept();
  });

  await confirmButton.click();

  await expect(
    page.getByText('Specification replacement complete'),
  ).toBeVisible({ timeout: 60_000 });

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelId}/model-validation$`),
  );

  await page.goto(`/workspace/${modelId}/model-studio`);

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelId}/model-studio$`),
    { timeout: 60_000 },
  );
}

async function prepareModel(browser: Browser): Promise<void> {
  setupContext = await browser.newContext({
    baseURL: BASE_URL,
    storageState: AUTH_FILE,
  });

  const page = await setupContext.newPage();
  const model = await createScenarioModel(page);
  createdModelName = model.modelName;

  await importGenerationSpecification(page, model.modelId);

  await page.getByRole('button', {
    name: 'Continue to Validation',
    exact: true,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${model.modelId}/model-validation$`),
  );

  await expect(
    page.getByText('Ready for Population', { exact: true }),
  ).toBeVisible({ timeout: 60_000 });

  await page.getByRole('button', {
    name: 'Continue to Population',
    exact: true,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${model.modelId}/data-model/population$`),
  );

  await expect(
    page.getByRole('heading', {
      name: 'Population Plan',
      exact: true,
    }),
  ).toBeVisible();

  await expect(page.locator('#population-target')).toBeVisible();

  await page.getByRole('button', {
    name: 'Review & Accept Plan',
    exact: true,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${model.modelId}/data-model/generate$`),
    { timeout: 60_000 },
  );

  scenario = model;
}

async function deleteScenarioModel(): Promise<void> {
  if (!setupContext || !createdModelName) return;

  const page = await setupContext.newPage();
  try {
    await page.goto('/workspace');

    await expect(page.locator('app-workspace')).toBeVisible();

    const card = page.locator('.dataModel-card').filter({
      has: page.getByRole('heading', {
        name: createdModelName,
        exact: true,
      }),
    });

    const count = await card.count();
    if (count === 0) return;

    expect(
      count,
      'Cleanup must identify exactly one MS30-owned model before deletion',
    ).toBe(1);
    const actionsButton = card.getByRole('button', {
      name: 'Data Model actions',
    });
    await actionsButton.click({ timeout: 8_000 });

    const expanded = await actionsButton.getAttribute('aria-expanded');
    await expect(actionsButton).toHaveAttribute('aria-expanded', 'true', {
      timeout: 5_000,
    });

    const menu = card.getByRole('menu');
    await expect(menu).toBeVisible({ timeout: 5_000 });

    const editMenuItem = menu.getByRole('menuitem', {
      name: /Edit/,
    });

    await expect(editMenuItem).toBeVisible({ timeout: 5_000 });

    await editMenuItem.click({ timeout: 8_000 });

    const editDialog = page.getByRole('dialog', {
      name: 'Edit Data Model',
    });

    await expect(editDialog).toBeVisible();

    await editDialog.locator('button.delete-button').click();

    const confirmation = page.getByRole('dialog', {
      name: 'Delete this Data Model?',
    });

    await expect(confirmation).toBeVisible();
    await expect(confirmation).toContainText(createdModelName);

    const confirmButton = confirmation.locator('button.confirm-button');
    await expect(confirmButton).toBeEnabled();
    await confirmButton.click();

    await expect(card).toHaveCount(0, { timeout: 30_000 });
  } finally {
    await page.close();
  }
}

async function attachEvidence(
  testInfo: TestInfo,
  filename: string,
  evidence: Record<string, unknown>,
): Promise<void> {
  await testInfo.attach(filename, {
    body: JSON.stringify(evidence, null, 2),
    contentType: 'application/json',
  });
}

test.describe('MS30 - Generation lifecycle', () => {
  test.describe.configure({ timeout: 600_000 });

  test.beforeAll(async ({ browser }) => {
    await prepareModel(browser);
  });

  test.afterAll(async () => {
    try {
      await deleteScenarioModel();
    } finally {
      await setupContext?.close();
      setupContext = undefined;
    }
  });

  test('MS30-01: A new generation job starts and completes', async ({
    page,
  }, testInfo) => {
    const current = requireScenario();

    await page.goto(generationUrl(current.modelId));

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${current.modelId}/data-model/generate$`),
    );

    await page.getByRole('button', {
      name: 'Start Generation',
      exact: true,
    }).click();

    await expect(
      page.getByText('Generation completed', { exact: true }),
    ).toBeVisible({ timeout: 240_000 });

    await expect(page).toHaveURL(
      new RegExp(
        `/workspace/${current.modelId}/data-model/generate/[^/]+$`,
      ),
      { timeout: 60_000 },
    );

    const match = page.url().match(/\/data-model\/generate\/([^/]+)$/);
    expect(match, 'Expected job ID in job-specific Generate URL').not.toBeNull();

    const jobId = match![1];
    const job = await getGenerationJob(page, current.modelId, jobId);

    expect(job.data_model_id).toBe(current.modelId);
    expect(job.job_id).toBe(jobId);
    expect(job.status).toBe('COMPLETED');
    expect(job.total_target_rows).toBe(TARGET_ROWS);
    expect(job.total_generated_rows).toBe(TARGET_ROWS);
    expect(job.progress).toBe(1);

    // Continue through the actual Generate workflow action.
    await page.getByRole('button', {
      name: 'Continue to Results',
      exact: true,
    }).click();

    const expectedResultsUrl =
      `/workspace/${current.modelId}/data-model/results/${jobId}`;

    await expect(page).toHaveURL(
      new RegExp(`${expectedResultsUrl}$`),
      { timeout: 60_000 },
    );

    // Verify the persisted execution summary is rendered.
    const executionSummary = page.locator(
      'app-results-execution-summary',
    );

    await expect(
      executionSummary.getByText('Generation completed', {
        exact: true,
      }),
    ).toBeVisible({ timeout: 60_000 });

    await expect(
      executionSummary.getByText(
        /12\s*\/\s*12\s*rows generated/,
      ),
    ).toBeVisible();

    // Verify generated artifacts are loaded into the Results table.
    await expect(
      page.getByRole('heading', {
        name: 'Generated Files',
        exact: true,
      }),
    ).toBeVisible();

    const generatedFileRows = page.locator(
      'app-generated-files .simple-table-row',
    );

    await expect(generatedFileRows.first()).toBeVisible({
      timeout: 60_000,
    });

    const generatedFileCount = await generatedFileRows.count();
    expect(generatedFileCount).toBeGreaterThan(0);

    const firstGeneratedFile =
      (await generatedFileRows.first().innerText()).trim();

    // The Results component automatically selects the first artifact
    // and loads its preview.
    const previewRows = page.locator(
      'app-artifact-preview .simple-table-row',
    );

    await expect(previewRows.first()).toBeVisible({
      timeout: 60_000,
    });

    const previewRowCount = await previewRows.count();
    expect(previewRowCount).toBeGreaterThan(0);

    const resultsUrl = page.url();

    await attachEvidence(testInfo, 'ms30-01-new-job-completed.json', {
      model_id: current.modelId,
      job_id: jobId,
      status: job.status,
      total_target_rows: job.total_target_rows,
      total_generated_rows: job.total_generated_rows,
      progress: job.progress,
      resulting_url: resultsUrl,
      results_page: {
        execution_status_visible: true,
        generated_rows_visible: true,
        generated_file_count: generatedFileCount,
        first_generated_file: firstGeneratedFile,
        preview_row_count: previewRowCount,
      },
    });
  });

  test('MS30-02: An existing CREATED job starts through Retry Start', async ({
    page,
  }, testInfo) => {
    const current = requireScenario();

    await page.goto(generationUrl(current.modelId));

    const beforeCreation = await listGenerationJobs(page, current.modelId);

    const createdJob = await createGenerationJob(page, current.modelId);

    expect(createdJob.data_model_id).toBe(current.modelId);
    expect(createdJob.job_id).toBeTruthy();
    expect(createdJob.status).toBe('CREATED');
    expect(createdJob.total_target_rows).toBe(TARGET_ROWS);
    expect(createdJob.total_generated_rows).toBe(0);
    expect(
      beforeCreation.some((job) => job.job_id === createdJob.job_id),
    ).toBe(false);

    const persistedCreatedJob = await getGenerationJob(
      page,
      current.modelId,
      createdJob.job_id,
    );

    expect(persistedCreatedJob.status).toBe('CREATED');
    expect(persistedCreatedJob.job_id).toBe(createdJob.job_id);

    await page.goto(generationUrl(current.modelId, createdJob.job_id));

    await expect(page).toHaveURL(
      new RegExp(
        `/workspace/${current.modelId}/data-model/generate/${createdJob.job_id}$`,
      ),
    );

    await expect(
      page.getByRole('button', {
        name: 'Retry Start',
        exact: true,
      }),
    ).toBeVisible();

    await expect(
      page.getByRole('button', {
        name: 'Retry Start',
        exact: true,
      }),
    ).toBeEnabled();

    await page.getByRole('button', {
      name: 'Retry Start',
      exact: true,
    }).click();

    await expect(
      page.getByText('Generation completed', { exact: true }),
    ).toBeVisible({ timeout: 240_000 });

    const completedJob = await getGenerationJob(
      page,
      current.modelId,
      createdJob.job_id,
    );

    expect(completedJob.data_model_id).toBe(current.modelId);
    expect(completedJob.job_id).toBe(createdJob.job_id);
    expect(completedJob.status).toBe('COMPLETED');
    expect(completedJob.total_target_rows).toBe(TARGET_ROWS);
    expect(completedJob.total_generated_rows).toBe(TARGET_ROWS);
    expect(completedJob.progress).toBe(1);

    const jobsAfterRetry = await listGenerationJobs(page, current.modelId);

    expect(jobsAfterRetry).toHaveLength(beforeCreation.length + 1);
    expect(
      jobsAfterRetry.filter((job) => job.job_id === createdJob.job_id),
    ).toHaveLength(1);

    await attachEvidence(testInfo, 'ms30-02-created-job-retry.json', {
      model_id: current.modelId,
      job_id: createdJob.job_id,
      initial_status: persistedCreatedJob.status,
      final_status: completedJob.status,
      total_target_rows: completedJob.total_target_rows,
      total_generated_rows: completedJob.total_generated_rows,
      progress: completedJob.progress,
      job_count_before_creation: beforeCreation.length,
      job_count_after_retry: jobsAfterRetry.length,
      created_job_occurrences: jobsAfterRetry.filter(
        (job) => job.job_id === createdJob.job_id,
      ).length,
      resulting_url: page.url(),
    });
  });
});
