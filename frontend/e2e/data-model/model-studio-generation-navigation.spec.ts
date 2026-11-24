import { test, expect, BrowserContext, Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { resolve } from 'node:path';

const ENTITY = 'TestRecord';
const TARGET_ROWS = 12;
const BASE_URL =
  process.env.FORGE_E2E_BASE_URL ?? 'http://127.0.0.1:18876';

const AUTH_FILE = resolve(
  __dirname,
  '../../playwright/.auth/isolated-owner.json',
);

interface Scenario {
  modelId: string;
  modelName: string;
  jobId: string;
  modelUrl: string;
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
    throw new Error('MS29 shared generation scenario was not initialized.');
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

async function createScenarioModel(page: Page): Promise<{
  modelId: string;
  modelName: string;
  modelUrl: string;
}> {
  const uniqueId = `${Date.now()}-${randomUUID().slice(0, 8)}`;
  const modelName = `FORGE MS29 E2E ${uniqueId}`;

  await page.goto('/workspace');
  await expect(page.locator('app-workspace')).toBeVisible();

  await page.locator('.create-dataModel-card').click();

  const dialog = page.getByRole('dialog', { name: 'New Data Model' });
  await expect(dialog).toBeVisible();
  await page.locator('#data-model-name').fill(modelName);
  await page.locator('#data-model-description').fill(
    `MS29 generation navigation scenario ${uniqueId}`,
  );

  const saveButton = dialog.locator('button.save-button');
  await expect(saveButton).toBeEnabled();
  await saveButton.click();

  await expect(page).toHaveURL(
    /\/workspace\/[^/]+\/model-studio$/,
    { timeout: 30_000 },
  );

  const modelUrl = page.url();
  const match = modelUrl.match(/\/workspace\/([^/]+)\/model-studio$/);

  expect(match, 'Expected model ID in Model Studio URL').not.toBeNull();

  return {
    modelId: match![1],
    modelName,
    modelUrl,
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
    `${ENTITY},MS29 generation navigation test entity,${TARGET_ROWS},FIXED`,
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
    name: /^Preview CSV import$/,
  }).click();

  const review = page.locator('section[aria-label="CSV import review"]');
  await expect(review).toBeVisible();
  await expect(
    review.getByText('Ready to apply', { exact: true }),
  ).toBeVisible({ timeout: 60_000 });

  await page.getByRole('button', {
    name: /Apply additions & open Model Studio/,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelId}/model-studio$`),
    { timeout: 60_000 },
  );
}

async function acceptPopulationPlan(
  page: Page,
  modelId: string,
): Promise<void> {
  await page.goto(
    `/workspace/${modelId}/data-model/population`,
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
    new RegExp(`/workspace/${modelId}/data-model/generate$`),
    { timeout: 60_000 },
  );
}

async function startAndCaptureJob(
  page: Page,
  modelId: string,
): Promise<string> {
  await page.getByRole('button', {
    name: 'Start Generation',
    exact: true,
  }).click();

  await expect(
    page.getByText('Generation completed', { exact: true }),
  ).toBeVisible({ timeout: 240_000 });

  await expect(page).toHaveURL(
    new RegExp(
      `/workspace/${modelId}/data-model/generate/[^/]+$`,
    ),
    { timeout: 60_000 },
  );

  const match = page.url().match(
    /\/data-model\/generate\/([^/]+)$/,
  );

  expect(match, 'Expected job ID in job-specific Generate URL').not.toBeNull();

  const job = await getGenerationJob(page, modelId, match![1]);
  expect(job.data_model_id).toBe(modelId);
  expect(job.job_id).toBe(match![1]);
  expect(job.status).toBe('COMPLETED');

  return match![1];
}

async function prepareScenario(
  browser: import('@playwright/test').Browser,
): Promise<void> {
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

  await acceptPopulationPlan(page, model.modelId);
  const jobId = await startAndCaptureJob(page, model.modelId);

  scenario = {
    ...model,
    jobId,
  };
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
      'Cleanup must identify exactly one MS29-owned model before deletion',
    ).toBe(1);

    await card.getByRole('button', {
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
  testInfo: import('@playwright/test').TestInfo,
  filename: string,
  evidence: Record<string, unknown>,
): Promise<void> {
  await testInfo.attach(filename, {
    body: JSON.stringify(evidence, null, 2),
    contentType: 'application/json',
  });
}

test.describe('MS29 - Generation navigation and job context isolation', () => {
  test.describe.configure({ timeout: 600_000 });

  test.beforeAll(async ({ browser }) => {
    await prepareScenario(browser);
  });

  test.afterAll(async () => {
    try {
      await deleteScenarioModel();
    } finally {
      await setupContext?.close();
      setupContext = undefined;
    }
  });

  test('MS29-01: Completed generation returns to Population', async ({
    page,
  }, testInfo) => {
    const current = requireScenario();

    await page.goto(generationUrl(current.modelId, current.jobId));

    const job = await getGenerationJob(
      page,
      current.modelId,
      current.jobId,
    );

    expect(job.status).toBe('COMPLETED');

    await page.getByRole('button', {
      name: 'Back to Population',
      exact: true,
    }).click();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${current.modelId}/data-model/population$`),
    );

    await expect(
      page.getByRole('heading', {
        name: 'Population Plan',
        exact: true,
      }),
    ).toBeVisible();

    await attachEvidence(testInfo, 'ms29-01-population-navigation.json', {
      model_id: current.modelId,
      job_id: current.jobId,
      job_status: job.status,
      resulting_url: page.url(),
    });
  });

  test('MS29-02: Re-accepting the population plan opens a new execution', async ({
    page,
  }, testInfo) => {
    const current = requireScenario();

    await acceptPopulationPlan(page, current.modelId);

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${current.modelId}/data-model/generate$`),
    );

    await attachEvidence(testInfo, 'ms29-02-new-execution-route.json', {
      model_id: current.modelId,
      previous_job_id: current.jobId,
      resulting_url: page.url(),
    });
  });

  test('MS29-03: Job-less Generate route contains no stale execution state', async ({
    page,
  }, testInfo) => {
    const current = requireScenario();

    await page.goto(generationUrl(current.modelId));

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${current.modelId}/data-model/generate$`),
    );

    await expect(
      page.getByText('Generation is ready', { exact: true }),
    ).toBeVisible();

    await expect(
      page.getByText('No entity execution data yet', { exact: true }),
    ).toBeVisible();

    await expect(
      page.getByText('Waiting for generation activity', { exact: true }),
    ).toBeVisible();

    await expect(
      page.getByText('Recovery information is not available yet', {
        exact: true,
      }),
    ).toBeVisible();

    await expect(page.locator('body')).not.toContainText(current.jobId);

    await attachEvidence(testInfo, 'ms29-03-clean-execution-state.json', {
      model_id: current.modelId,
      previous_job_id: current.jobId,
      resulting_url: page.url(),
      entity_execution_empty: true,
      activity_empty: true,
      checkpoint_unavailable: true,
    });
  });

  test('MS29-04: Previous job-specific URL restores persisted execution', async ({
    page,
  }, testInfo) => {
    const current = requireScenario();

    await page.goto(generationUrl(current.modelId, current.jobId));

    const job = await getGenerationJob(
      page,
      current.modelId,
      current.jobId,
    );

    expect(job.data_model_id).toBe(current.modelId);
    expect(job.job_id).toBe(current.jobId);
    expect(job.status).toBe('COMPLETED');
    expect(job.total_generated_rows).toBe(job.total_target_rows);
    expect(job.progress).toBe(1);

    await expect(
      page.getByText('Generation completed', { exact: true }),
    ).toBeVisible();

    await attachEvidence(testInfo, 'ms29-04-restored-generation-job.json', {
      model_id: current.modelId,
      job_id: current.jobId,
      status: job.status,
      total_target_rows: job.total_target_rows,
      total_generated_rows: job.total_generated_rows,
      progress: job.progress,
      resulting_url: page.url(),
    });
  });

  test('MS29-05: Switching between generation jobs isolates execution context', async ({
    page,
  }, testInfo) => {
    const current = requireScenario();

    await acceptPopulationPlan(page, current.modelId);
    const secondJobId = await startAndCaptureJob(page, current.modelId);

    expect(secondJobId).not.toBe(current.jobId);

    const secondJob = await getGenerationJob(
      page,
      current.modelId,
      secondJobId,
    );

    await page.goto(generationUrl(current.modelId, current.jobId));

    const firstRestored = await getGenerationJob(
      page,
      current.modelId,
      current.jobId,
    );

    expect(firstRestored.job_id).toBe(current.jobId);
    expect(firstRestored.status).toBe('COMPLETED');

    await expect(
      page.getByText('Generation completed', { exact: true }),
    ).toBeVisible();

    await page.goto(generationUrl(current.modelId, secondJobId));

    const secondRestored = await getGenerationJob(
      page,
      current.modelId,
      secondJobId,
    );

    expect(secondRestored.job_id).toBe(secondJobId);
    expect(secondRestored.data_model_id).toBe(current.modelId);
    expect(secondRestored.status).toBe('COMPLETED');

    await expect(
      page.getByText('Generation completed', { exact: true }),
    ).toBeVisible();

    await page.goto(generationUrl(current.modelId, current.jobId));

    const firstRestoredAgain = await getGenerationJob(
      page,
      current.modelId,
      current.jobId,
    );

    expect(firstRestoredAgain.job_id).toBe(current.jobId);

    await attachEvidence(testInfo, 'ms29-05-job-context-isolation.json', {
      model_id: current.modelId,
      first_job: {
        job_id: current.jobId,
        status: firstRestoredAgain.status,
        progress: firstRestoredAgain.progress,
      },
      second_job: {
        job_id: secondJobId,
        status: secondJob.status,
        progress: secondJob.progress,
      },
      final_url: page.url(),
      job_ids_are_distinct: current.jobId !== secondJobId,
    });
  });

  test('MS29-06: Refresh preserves the clean execution landing state', async ({
    page,
  }, testInfo) => {
    const current = requireScenario();

    await page.goto(generationUrl(current.modelId));
    await page.reload();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${current.modelId}/data-model/generate$`),
    );

    await expect(
      page.getByText('No entity execution data yet', { exact: true }),
    ).toBeVisible();

    await expect(
      page.getByText('Waiting for generation activity', { exact: true }),
    ).toBeVisible();

    await expect(
      page.getByText('Recovery information is not available yet', {
        exact: true,
      }),
    ).toBeVisible();

    await expect(page.locator('body')).not.toContainText(current.jobId);

    await attachEvidence(testInfo, 'ms29-06-clean-state-after-refresh.json', {
      model_id: current.modelId,
      previous_job_id: current.jobId,
      resulting_url: page.url(),
      entity_execution_empty: true,
      activity_empty: true,
      checkpoint_unavailable: true,
    });
  });
});
